"""CALLM agent server: drives the model under test through one CALLM call.

Thin by design. Everything the environment owns (prompts, toolsets, handoffs,
tool execution, the caller, scoring) lives in the `callm` resources server;
this server only runs the shared turn loop (`callm.loop.run_episode`) with the
policy behind `model_server` and the environment behind HTTP.

Policy calls go through `url_path_for_run`, so a training model server captures
tokens per call, including calls made under a swapped system prompt.
"""

from __future__ import annotations

import json
from time import time
from typing import Any, Literal

from fastapi import Body, Request
from pydantic import ConfigDict

from callm.llm import add_usage, new_usage, parse_message, parse_response, responses_request
from callm.loop import run_episode
from nemo_gym.base_resources_server import BaseRunRequest, BaseVerifyResponse
from nemo_gym.base_responses_api_agent import BaseResponsesAPIAgentConfig, SimpleResponsesAPIAgent
from nemo_gym.config_types import ModelServerRef, ResourcesServerRef
from nemo_gym.openai_utils import NeMoGymResponse, NeMoGymResponseCreateParamsNonStreaming
from nemo_gym.rollout_collection import NG_FAILURE_CLASS_KEY
from nemo_gym.server_utils import get_response_json, raise_for_status
from responses_api_models.vllm_model.app import VLLMConverter, split_responses_input_output_items

FAILURE_CLASS = "callm_agent_error"
HISTORY_KEYS = ("role", "content", "tool_calls", "tool_call_id")


def slim_calls(calls: list[dict[str, Any]], swaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace each call's system prompt text by the index of the swap that served it."""
    index = {s["system_prompt"]: k for k, s in enumerate(swaps)}
    return [{**{k: v for k, v in c.items() if k != "system"}, "swap": index.get(c.get("system"))} for c in calls]


class CallmAgentConfig(BaseResponsesAPIAgentConfig):
    resources_server: ResourcesServerRef
    model_server: ModelServerRef
    max_exchanges: int = 30
    max_tool_rounds: int = 8
    # responses: the model server's /v1/responses (needed for reasoning models that only take tools there)
    policy_api: Literal["chat_completions", "responses"] = "chat_completions"


class CallmRunRequest(BaseRunRequest):
    model_config = ConfigDict(extra="allow")
    industry: str
    case_key: str


class CallmVerifyResponse(BaseVerifyResponse):
    model_config = ConfigDict(extra="allow")


class _HttpEnv:
    """Loop env port over the resources server, bound to one session cookie jar."""

    def __init__(self, agent: "CallmAgent", cookies: Any):
        self.agent = agent
        self.cookies = cookies

    async def _post(self, path: str, payload: Any) -> Any:
        response = await self.agent.server_client.post(
            server_name=self.agent.config.resources_server.name,
            url_path=path,
            json=payload,
            cookies=self.cookies,
        )
        await raise_for_status(response)
        return await get_response_json(response)

    async def state(self) -> dict[str, Any]:
        return await self._post("/session_state", {})

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"/{name}", arguments)

    async def end_turn(self, agent_text: str) -> dict[str, Any]:
        return await self._post("/end_turn", {"agent_text": agent_text})


class _ServerPolicy:
    """Loop policy port over the Gym model server: chat completions or the Responses API."""

    def __init__(self, agent: "CallmAgent", body: CallmRunRequest, params: dict[str, Any]):
        self.agent = agent
        self.body = body
        self.api = agent.config.policy_api
        self.usage = new_usage()
        # One small record per policy call. Its request is rebuilt for the latency pass from the
        # episode's history (stored once) + the active prompt's swap index + the offered tool names.
        self.calls: list[dict[str, Any]] = []
        self.sampling = {k: params[k] for k in ("temperature", "top_p") if params.get(k) is not None}
        if params.get("max_output_tokens"):
            key = "max_output_tokens" if self.api == "responses" else "max_tokens"
            self.sampling[key] = params["max_output_tokens"]

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if self.api == "responses":
            path, payload = "/v1/responses", {**responses_request(messages, tools), **self.sampling}
        else:
            path, payload = "/v1/chat/completions", {"messages": messages, "tools": tools, **self.sampling}
        record: dict[str, Any] = {"i": len(self.calls), "api": self.api, "t_start": time(),
                                  "n_history": len(messages) - 1, "system": messages[0]["content"],
                                  "tools": [(t.get("function") or t).get("name") for t in tools]}
        self.calls.append(record)
        try:
            response = await self.agent.server_client.post(
                server_name=self.agent.config.model_server.name,
                url_path=self.agent.url_path_for_run(path, self.body),
                json=payload,
            )
            record["status"] = getattr(response, "status", None) or getattr(response, "status_code", None)
            await raise_for_status(response)
            result = await get_response_json(response)
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"[:300]
            raise
        finally:
            record["latency_ms"] = round((time() - record["t_start"]) * 1000)
        add_usage(self.usage, result.get("usage"))
        parsed = parse_response(result) if self.api == "responses" else parse_message(result["choices"][0]["message"])
        record.update({
            "served_model": result.get("model"),
            "usage": result.get("usage"),
            "finish": result.get("status") if self.api == "responses" else result["choices"][0].get("finish_reason"),
            "text": parsed.get("content") or "",
            "tool_calls": [{"name": c["name"], "arguments": c["arguments"]} for c in parsed.get("tool_calls") or []],
        })
        return parsed


class CallmAgent(SimpleResponsesAPIAgent):
    config: CallmAgentConfig  # pyright: ignore[reportIncompatibleVariableOverride]

    async def responses(self, body: NeMoGymResponseCreateParamsNonStreaming = Body()) -> NeMoGymResponse:
        raise NotImplementedError("CALLM episodes run through /run")

    async def run(self, request: Request, body: CallmRunRequest) -> CallmVerifyResponse:  # pyright: ignore[reportIncompatibleMethodOverride]
        params = body.responses_create_params.model_dump(exclude_unset=True)
        seed = await self.server_client.post(
            server_name=self.config.resources_server.name,
            url_path="/seed_session",
            json=body.model_dump(mode="json"),
            cookies=request.cookies,
        )
        await raise_for_status(seed)
        env = _HttpEnv(self, seed.cookies)
        policy = _ServerPolicy(self, body, params)
        try:
            history = await run_episode(
                policy,
                env,
                max_exchanges=self.config.max_exchanges,
                max_tool_rounds=self.config.max_tool_rounds,
            )
        except Exception as error:  # noqa: BLE001 -- one bad rollout must not abort the collection
            try:  # /verify also ends the session; release it, discard the score
                await env._post("/verify", body.model_dump(mode="json") | {"response": self._response(body, params, [])})
            except Exception:  # noqa: BLE001
                pass
            return CallmVerifyResponse.model_validate(
                body.model_dump(mode="json")
                | {
                    "reward": 0.0,
                    "response": self._response(body, params, []),
                    NG_FAILURE_CLASS_KEY: FAILURE_CLASS,
                    "usage": {"policy": policy.usage},
                    "policy_calls": slim_calls(policy.calls, []),
                    "error": f"{type(error).__name__}: {error}"[:500],
                }
            )
        response = self._response(body, params, history)
        result = await env._post("/verify", body.model_dump(mode="json") | {"response": response})
        swaps = result.get("system_prompt_swaps") or []
        system0 = [{"role": "system", "content": swaps[0]["system_prompt"]}] if swaps else []
        result["responses_create_params"] = self._create_params(params, history, system0)
        result["usage"] = {"policy": policy.usage, **(result.get("usage") or {})}
        result["policy_calls"] = slim_calls(policy.calls, result.get("system_prompt_swaps") or [])
        result["policy_history"] = [{k: m[k] for k in HISTORY_KEYS if m.get(k) is not None} for m in history]
        return CallmVerifyResponse.model_validate(result)

    @staticmethod
    def _items(history: list[dict[str, Any]]) -> tuple[list[Any], list[Any]]:
        """Chat history -> (input items, output items). The front desk speaks
        first, so its greeting folds into the input side (tau2 convention)."""
        if not history:
            return [], []
        history = [{k: v for k, v in m.items() if k != "responses_output"} for m in history]
        items = VLLMConverter(return_token_id_information=True).chat_completions_messages_to_responses_items(history)
        input_items, output_items = split_responses_input_output_items(items)
        input_items += output_items[:1]
        input_items_2, output_items = split_responses_input_output_items(output_items[1:])
        return input_items + input_items_2, output_items

    def _create_params(self, params: dict[str, Any], history: list[dict[str, Any]],
                       system0: list[dict[str, Any]]) -> dict[str, Any]:
        """Trajectory input: the entry agent's prompt as the environment served it,
        then the conversation. Later swaps are in `system_prompt_swaps`."""
        input_items, _ = self._items(history)
        return {"input": system0 + list(params.get("input") or []) + input_items, "model": params.get("model") or ""}

    def _response(self, body: CallmRunRequest, params: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
        _, output_items = self._items(history)
        if not output_items:
            output_items = [{
                "type": "message", "role": "assistant", "status": "completed", "id": "msg_0",
                "content": [{"type": "output_text", "text": "", "annotations": []}],
            }]
        return json.loads(json.dumps({
            "id": f"callm-{body.industry}-{body.case_key}",
            "created_at": int(time()),
            "object": "response",
            "model": params.get("model") or "",
            "output": output_items,
            "parallel_tool_calls": False,
            "tool_choice": "auto",
            "tools": [],
        }, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o)))


if __name__ == "__main__":
    CallmAgent.run_webserver()
