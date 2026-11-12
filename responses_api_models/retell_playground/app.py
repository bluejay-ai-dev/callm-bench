"""Gym model server that serves Retell's Tell-1 (or any Retell LLM model) as chat completions.

Retell exposes Tell-1 only through `POST /agent-playground-completion/{agent_id}`: stateless,
full history in, new messages out, tools run by Retell. To keep CALLM semantics identical to
every other model:

- Each distinct (system prompt, toolset) gets its own Retell LLM + agent, created on first use
  and remembered in `agents.json` next to this file. The prompt is the exact CALLM prompt the
  environment served; handbook presets are all off, per Retell's guidance.
- Every tool is mocked (`tool_mocks`, match any input) and set not to speak after execution, so
  Retell never reaches a real tool. The reply is cut at the first tool call and returned as an
  OpenAI `tool_calls` message; the CALLM environment runs the tool against its own per-call
  SQLite and sends the real result back in the next request's history.
- A handoff is an ordinary tool call here, so the next request carries the new agent's prompt
  and maps to that agent's Retell agent, with the history unchanged.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import Body, Request

from responses_api_models.openai_model.app import SimpleModelServer, SimpleModelServerConfig

AGENTS_FILE = Path(__file__).parent / "agents.json"
HANDBOOK_OFF = {k: False for k in (
    "default_personality", "conversational_personality", "natural_filler_words", "high_empathy",
    "echo_verification", "nato_phonetic_alphabet", "speech_normalization", "smart_matching",
    "ai_disclosure", "scope_boundaries")}
UNUSED_TOOL_URL = "https://callm.invalid/tools/"  # never called: every tool is mocked


class RetellPlaygroundConfig(SimpleModelServerConfig):
    voice_id: str = "cartesia-Cleo"  # required by create-agent; the playground is text only
    retries: int = 6


def retell_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chat-completions history (system prompt excluded) -> playground messages."""
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "user" and m.get("content"):
            out.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            if m.get("content"):
                out.append({"role": "agent", "content": m["content"]})
            for c in m.get("tool_calls") or []:
                fn = c.get("function") or {}
                out.append({"role": "tool_call_invocation", "tool_call_id": c["id"], "name": fn.get("name"),
                            "arguments": fn.get("arguments") or "{}"})
        elif role == "tool":
            out.append({"role": "tool_call_result", "tool_call_id": m.get("tool_call_id"),
                        "content": m.get("content") or "", "successful": True})
    return out


def first_turn(new: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Agent text up to the first tool call, plus that call and any calls made alongside it."""
    text, calls = [], []
    for m in new:
        role = m.get("role")
        if role == "tool_call_invocation":
            calls.append({"id": m["tool_call_id"], "type": "function",
                          "function": {"name": m["name"], "arguments": m.get("arguments") or "{}"}})
        elif calls:
            break  # a mocked result or text after the call: Retell went past what CALLM has run
        elif role == "agent" and m.get("content"):
            text.append(m["content"].strip())
    return " ".join(t for t in text if t), calls


class RetellPlaygroundServer(SimpleModelServer):
    config: RetellPlaygroundConfig  # pyright: ignore[reportIncompatibleVariableOverride]

    def model_post_init(self, context: Any) -> None:
        super().model_post_init(context)
        self._http = httpx.AsyncClient(base_url=self.config.openai_base_url.rstrip("/"), timeout=60,
                                       headers={"Authorization": f"Bearer {self.config.openai_api_key}"})
        self._agents: dict[str, str] = json.loads(AGENTS_FILE.read_text()) if AGENTS_FILE.is_file() else {}
        self._creating: dict[str, asyncio.Lock] = {}

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self.config.retries):
            resp = await self._http.post(path, json=payload)
            if resp.status_code != 429 and resp.status_code < 500:
                break
            await asyncio.sleep(min(30, 2 ** attempt))  # Tell-1 runs on ~10 QPS of shared capacity
        if resp.status_code >= 400:
            raise RuntimeError(f"Retell {path} {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def _agent_for(self, system: str, tools: list[dict[str, Any]]) -> str:
        key = hashlib.sha256(json.dumps([self.config.openai_model, system, tools], sort_keys=True).encode()).hexdigest()[:24]
        if key in self._agents:
            return self._agents[key]
        async with self._creating.setdefault(key, asyncio.Lock()):
            if key in self._agents:
                return self._agents[key]
            llm = await self._post("/create-retell-llm", {
                "general_prompt": system,
                "model_config": {"type": "cascading", "primary": {"model": self.config.openai_model}},
                "start_speaker": "agent",
                "general_tools": [{
                    "type": "custom", "name": fn["name"], "description": fn.get("description") or fn["name"],
                    "url": UNUSED_TOOL_URL + fn["name"], "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
                    "speak_during_execution": False, "speak_after_execution": False,
                } for fn in ((t.get("function") or t) for t in tools)],
            })
            agent = await self._post("/create-agent", {
                "agent_name": f"callm-phonebench-{key[:10]}", "voice_id": self.config.voice_id,
                "response_engine": {"type": "retell-llm", "llm_id": llm["llm_id"]},
                "handbook_config": HANDBOOK_OFF,
            })
            self._agents[key] = agent["agent_id"]
            AGENTS_FILE.write_text(json.dumps(self._agents, indent=1))
            return agent["agent_id"]

    async def chat_completions_dispatch(self, request: Request, body: dict[str, Any] = Body()):  # pyright: ignore[reportIncompatibleMethodOverride]
        messages = body.get("messages") or []
        system = "\n\n".join(m["content"] for m in messages if m.get("role") in ("system", "developer"))
        history = [m for m in messages if m.get("role") not in ("system", "developer")]
        tools = body.get("tools") or []
        agent_id = await self._agent_for(system, tools)
        payload = {
            "messages": retell_messages(history),
            "tool_mocks": [{"tool_name": (t.get("function") or t)["name"], "input_match_rule": {"type": "any"},
                            "output": "{}"} for t in tools],
        }
        async with self._semaphore:
            out = await self._post(f"/agent-playground-completion/{agent_id}", payload)
        text, calls = first_turn(out.get("messages") or [])
        message: dict[str, Any] = {"role": "assistant", "content": text or None}
        if calls:
            message["tool_calls"] = calls
        return {
            "id": f"retell-{agent_id}-{int(time.time() * 1000)}", "object": "chat.completion",
            "created": int(time.time()), "model": self.config.openai_model,
            "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop"}],
            "usage": None,  # the playground reports no token usage
        }


def _self_check() -> None:
    """History conversion and cutting a reply at the first tool call (`python app.py --self-check`)."""
    hist = [{"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "One moment.", "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": "{\"a\":1}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "{\"ok\":true}"}]
    assert [m["role"] for m in retell_messages(hist)] == ["user", "agent", "tool_call_invocation", "tool_call_result"]
    text, calls = first_turn([{"role": "agent", "content": "Let me check. "},
                              {"role": "tool_call_invocation", "tool_call_id": "t1", "name": "find", "arguments": "{}"},
                              {"role": "tool_call_result", "tool_call_id": "t1", "content": "{}"},
                              {"role": "agent", "content": "Found it."}])
    assert text == "Let me check." and [c["function"]["name"] for c in calls] == ["find"], (text, calls)
    print("retell_playground self-check ok")


if __name__ == "__main__":
    import sys

    if "--self-check" in sys.argv:
        _self_check()
    else:
        RetellPlaygroundServer.run_webserver()
