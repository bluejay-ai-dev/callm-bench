"""CALLM resources server: the environment side of a CALLM episode.

One server hosts every configured industry. Per rollout (keyed by the Gym
session cookie) it holds a `callm.env.Session`: a fresh seeded database on the
industry tool server, the multi-agent DAG position, and the caller simulator.

Routes
  /seed_session    row {industry, case_key} -> new session
  /session_state   active agent's system prompt (messages[0]) + toolset, done flag
  /{tool}          one route per pack tool; refused unless the active agent owns it
  /end_turn        agent's spoken text in, caller's reply out (pinned simulator model)
  /verify          conjunctive verdict + shaped reward; ends the session

The caller simulator is environment, never policy: it runs on
`user_model_server`, which must not be the model being trained.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Literal

from fastapi import Body, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from callm import bench
from callm.env import Session, ToolServers
from callm.llm import OpenAIChat
from callm.usersim import temperature
from nemo_gym.base_resources_server import (
    BaseResourcesServerConfig,
    BaseSeedSessionRequest,
    BaseSeedSessionResponse,
    BaseVerifyRequest,
    BaseVerifyResponse,
    SimpleResourcesServer,
)
from nemo_gym.config_types import ModelServerRef
from nemo_gym.server_utils import SESSION_ID_KEY, get_server_url

# Processes and live sessions stay out of the pydantic server model.
_SERVERS = ToolServers()
_SESSIONS: dict[str, Session] = {}
# Caller replies and tool calls block; asyncio's default pool (cpu+4 threads) caps
# concurrent rollouts well below what Gym dispatches.
_POOL = ThreadPoolExecutor(max_workers=64, thread_name_prefix="callm")


async def _blocking(fn: Callable[..., Any], *args: Any) -> Any:
    return await asyncio.get_running_loop().run_in_executor(_POOL, partial(fn, *args))


class CallmResourcesServerConfig(BaseResourcesServerConfig):
    user_model_server: ModelServerRef
    industries: list[str] = Field(default_factory=lambda: ["healthcare", "legal", "customer-support"])
    reward: Literal["conjunctive", "shaped"] = "conjunctive"
    # false for caller models that only take their default temperature (gpt-6-astra with reasoning)
    user_temperature: bool = True
    # recognizer profile name in src/callm/asr_profiles/; '' = caller text reaches the agent verbatim
    asr_profile: str = ""
    # draw each caller turn's recognizer result from the profile's real rates (see usersim.draw)
    asr_draws: bool = True
    # changes every draw; keep it fixed across the models of one benchmark version
    channel_seed: int = 0


class CallmSeedSessionRequest(BaseSeedSessionRequest):
    model_config = ConfigDict(extra="allow")
    industry: str
    case_key: str


class EndTurnRequest(BaseModel):
    agent_text: str = ""


class CallmVerifyRequest(BaseVerifyRequest):
    model_config = ConfigDict(extra="allow")
    industry: str
    case_key: str


class CallmVerifyResponse(CallmVerifyRequest, BaseVerifyResponse):
    conjunctive: float
    shaped: float
    tool_reward: float
    handoff_reward: float
    state_reward: float
    components: dict[str, Any]
    transcript: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    system_prompt_swaps: list[dict[str, Any]]
    final_state: Any
    ended_by: str
    usage: dict[str, Any] = {}
    user_calls: list[dict[str, Any]] = []
    asr_profile: str = ""
    attempt: int = 0


# Gym servers narrow `config` and add a FastAPI `request` param to route
# handlers; pyright can't model either, so those overrides are ignored.
class CallmResourcesServer(SimpleResourcesServer):
    config: CallmResourcesServerConfig  # pyright: ignore[reportIncompatibleVariableOverride]

    def setup_webserver(self) -> FastAPI:
        app = super().setup_webserver()
        app.post("/session_state")(self.session_state)
        app.post("/end_turn")(self.end_turn)
        tools = sorted(set().union(*(bench.tool_names(i) for i in self.config.industries)))
        reserved = {getattr(route, "path", "") for route in app.routes}
        for name in tools:
            if f"/{name}" in reserved:
                raise RuntimeError(f"tool {name!r} collides with a server route")
            app.post(f"/{name}")(self._tool_route(name))
        # Any other name is a tool the model made up: the episode records it and answers
        # UNKNOWN_TOOL instead of the request 404ing and crashing the rollout.
        app.post("/{name}")(self._any_tool)
        return app

    async def _any_tool(self, name: str, request: Request,
                        arguments: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        return await _blocking(self._session(request).call_tool, name, arguments)

    def _session(self, request: Request) -> Session:
        session = _SESSIONS.get(request.session[SESSION_ID_KEY])
        if session is None:
            raise HTTPException(status_code=404, detail="no CALLM session; call /seed_session first")
        return session

    def _user_llm(self, task: dict[str, Any]) -> OpenAIChat:
        return OpenAIChat(
            "callm-caller",  # the model server substitutes its configured model
            base_url=f"{get_server_url(self.config.user_model_server.name)}/v1",
            api_key="unused",
            temperature=temperature(task) if self.config.user_temperature else None,
        )

    async def seed_session(self, request: Request, body: CallmSeedSessionRequest) -> BaseSeedSessionResponse:  # pyright: ignore[reportIncompatibleMethodOverride]
        if body.industry not in self.config.industries:
            raise HTTPException(status_code=400, detail=f"industry {body.industry!r} not configured")
        session_id = request.session[SESSION_ID_KEY]
        old = _SESSIONS.pop(session_id, None)
        if old is not None:
            old.close()
        server = await _blocking(_SERVERS.for_task, body.industry, body.case_key)
        task = bench.load_task(body.industry, body.case_key)
        # Gym's per-task repeat index keys the draws, so attempt k of a task is the same for every model.
        attempt = int((body.model_extra or {}).get("_ng_rollout_index") or 0)
        _SESSIONS[session_id] = Session(body.industry, body.case_key, server, self._user_llm(task),
                                        asr_profile=self.config.asr_profile, asr_draws=self.config.asr_draws,
                                        attempt=attempt, channel_seed=self.config.channel_seed)
        return BaseSeedSessionResponse()

    async def session_state(self, request: Request) -> dict[str, Any]:
        return self._session(request).state()

    def _tool_route(self, name: str):
        async def call(request: Request, arguments: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
            return await _blocking(self._session(request).call_tool, name, arguments)

        call.__name__ = f"tool_{name}"
        return call

    async def end_turn(self, request: Request, body: EndTurnRequest) -> dict[str, Any]:
        return await _blocking(self._session(request).end_turn, body.agent_text)

    async def verify(self, request: Request, body: CallmVerifyRequest) -> CallmVerifyResponse:  # pyright: ignore[reportIncompatibleMethodOverride]
        session = self._session(request)
        try:
            result, scored = await _blocking(session.score)
        finally:
            session.close()
            _SESSIONS.pop(request.session[SESSION_ID_KEY], None)
        reward = scored["conjunctive"] if self.config.reward == "conjunctive" else scored["shaped"]
        return CallmVerifyResponse(
            **body.model_dump(),
            reward=reward,
            conjunctive=scored["conjunctive"],
            shaped=scored["shaped"],
            tool_reward=scored["tool_reward"],
            handoff_reward=scored["handoff_reward"],
            state_reward=scored["state_reward"],
            components=scored["components"],
            transcript=result["transcript"],
            trace=result["trace"],
            system_prompt_swaps=result["system_prompt_swaps"],
            final_state=result["final_state"],
            ended_by=result["ended_by"],
            usage={"user": getattr(getattr(session.user, "llm", None), "usage", None)},
            user_calls=getattr(getattr(session.user, "llm", None), "calls", None) or [],
            asr_profile=session.asr_profile,
            attempt=session.attempt,
        )


if __name__ == "__main__":
    CallmResourcesServer.run_webserver()
