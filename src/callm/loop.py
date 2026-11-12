"""The one CALLM turn loop, shared by local runs and the NeMo Gym agent server.

Two-party conversation, tau2-bench shape: the model under test speaks first (a
front desk greets), may call tools mid-turn, then the caller replies. The loop
never decides prompts or tools itself — it asks the environment for the
active agent's system prompt (messages[0]) and toolset before every model
call, so a handoff tool swaps both in place while history carries over.

Ports:
- policy.chat(messages, tools) -> {"content", "tool_calls", "message"?}
- env.state() -> {"system_prompt", "tools", "done"}
- env.call_tool(name, arguments) -> tool result dict
- env.end_turn(agent_text) -> {"text", "done"}
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

MAX_EXCHANGES = 30       # caller replies before the call is cut off
MAX_TOOL_ROUNDS = 8      # model calls inside one agent turn

# Token bookkeeping a training model server (vLLM) attaches to assistant
# messages; carried into history so captured trajectories stay on-policy.
TOKEN_KEYS = ("prompt_token_ids", "generation_token_ids", "generation_log_probs")


class Policy(Protocol):
    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]: ...


class Env(Protocol):
    async def state(self) -> dict[str, Any]: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...
    async def end_turn(self, agent_text: str) -> dict[str, Any]: ...


def assistant_message(reply: dict[str, Any]) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": (reply.get("content") or None)}
    calls = reply.get("tool_calls") or []
    if calls:
        msg["tool_calls"] = [
            {"id": c["id"], "type": "function",
             "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])},
             **({"extra_content": c["extra_content"]} if c.get("extra_content") else {})}
            for c in calls
        ]
    raw = reply.get("message") or {}
    for key in TOKEN_KEYS:
        if raw.get(key) is not None:
            msg[key] = raw[key]
    if reply.get("responses_output"):
        msg["responses_output"] = reply["responses_output"]
    return msg


async def run_episode(
    policy: Policy,
    env: Env,
    *,
    max_exchanges: int = MAX_EXCHANGES,
    max_tool_rounds: int = MAX_TOOL_ROUNDS,
) -> list[dict[str, Any]]:
    """Play one call; returns the model's chat history (system prompts excluded)."""
    history: list[dict[str, Any]] = []
    state = await env.state()
    for _ in range(max_exchanges):
        agent_text = ""
        for _ in range(max_tool_rounds):
            messages = [{"role": "system", "content": state["system_prompt"]}, *history]
            reply = await policy.chat(messages, state["tools"])
            content = (reply.get("content") or "").strip()
            if content:
                agent_text = f"{agent_text} {content}".strip()
            history.append(assistant_message(reply))
            calls = reply.get("tool_calls") or []
            if not calls:
                break
            for call in calls:
                result = await env.call_tool(call["name"], call["arguments"])
                history.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
            state = await env.state()
            if state["done"]:
                break
        turn = await env.end_turn(agent_text)
        if turn["done"]:
            break
        if turn["text"]:
            history.append({"role": "user", "content": turn["text"]})
    return history


class LocalEnv:
    """Env port over an in-process Session (CLI runs and tests)."""

    def __init__(self, session):
        self.session = session

    async def state(self) -> dict[str, Any]:
        return self.session.state()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self.session.call_tool, name, arguments)

    async def end_turn(self, agent_text: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.session.end_turn, agent_text)


class ChatPolicy:
    """Policy port over a synchronous chat client (OpenAIChat, FakeChat)."""

    def __init__(self, llm):
        self.llm = llm

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        return await asyncio.to_thread(self.llm.chat, messages, tools)
