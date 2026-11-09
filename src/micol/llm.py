"""OpenAI-compatible chat completions client, plus a scripted fake for tests.

Any endpoint speaking the OpenAI chat API works (OpenAI, vLLM, NIM, a NeMo Gym
model server, ...) via base_url. Replies are normalized to
{"content", "tool_calls": [{"id", "name", "arguments"}], "message": raw dict}.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any


def parse_message(message: dict[str, Any]) -> dict[str, Any]:
    """Normalize one chat-completions assistant message dict."""
    calls = []
    for c in message.get("tool_calls") or []:
        fn = c.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        call = {"id": c.get("id"), "name": fn.get("name"), "arguments": args}
        if c.get("extra_content"):  # provider state the call must carry back (Gemini thought_signature)
            call["extra_content"] = c["extra_content"]
        calls.append(call)
    return {"content": message.get("content"), "tool_calls": calls, "message": message}


def new_usage() -> dict[str, int]:
    return {"input": 0, "cached": 0, "output": 0, "calls": 0}


def add_usage(total: dict[str, int], usage: dict[str, Any] | None) -> None:
    """Add one chat-completions or Responses API `usage` block to a running total."""
    if not usage:
        return
    details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    total["input"] += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    total["cached"] += int(details.get("cached_tokens") or 0)
    total["output"] += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total["calls"] += 1


class OpenAIChat:
    def __init__(self, model: str, *, base_url: str | None = None, api_key: str | None = None,
                 temperature: float | None = None):
        from openai import OpenAI

        self.model = model
        self.temperature = temperature
        self.usage = new_usage()
        self.calls: list[dict[str, Any]] = []  # timing + usage per call, for the trace
        self._client = OpenAI(
            base_url=base_url or os.environ.get("OPENAI_BASE_URL") or None,
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        )

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        t0 = time.time()
        completion = self._client.chat.completions.create(**kwargs)
        usage = completion.usage.model_dump() if completion.usage else None
        add_usage(self.usage, usage)
        self.calls.append({"t_start": t0, "latency_ms": round((time.time() - t0) * 1000),
                           "served_model": completion.model, "usage": usage,
                           "finish": completion.choices[0].finish_reason})
        return parse_message(completion.choices[0].message.model_dump(exclude_none=True))


class FakeChat:
    """Deterministic scripted LLM for tests: pops queued replies in order."""

    def __init__(self, script: list[dict[str, Any]]):
        self.script = list(script)

    def chat(self, messages, tools=None) -> dict[str, Any]:
        if not self.script:
            raise AssertionError("FakeChat script exhausted")
        step = self.script.pop(0)
        return {
            "content": step.get("content"),
            "tool_calls": [
                {"id": f"fake_{i}", "name": c["name"], "arguments": c.get("arguments", {})}
                for i, c in enumerate(step.get("tool_calls", []))
            ],
        }


def tool_decl(spec: dict[str, Any]) -> dict[str, Any]:
    """tools.json entry -> chat-completions function declaration."""
    params = dict(spec.get("inputSchema") or {"type": "object", "properties": {}})
    return {
        "type": "function",
        "function": {
            "name": spec["name"],
            "description": spec.get("description", spec["name"]),
            "parameters": params,
        },
    }


# ---------------------------------------------------------------- Responses API

def responses_request(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Chat history + chat-completions tools -> a Responses API request body.

    An assistant turn that came from the Responses API carries its raw output items
    (`responses_output`), replayed verbatim so reasoning items stay with their tool calls.
    """
    items: list[dict[str, Any]] = []
    for m in messages:
        role = m["role"]
        if role == "assistant" and m.get("responses_output"):
            items.extend(m["responses_output"])
        elif role == "assistant":
            if m.get("content"):
                items.append({"role": "assistant", "content": m["content"]})
            for c in m.get("tool_calls") or []:
                items.append({"type": "function_call", "call_id": c["id"],
                              "name": c["function"]["name"], "arguments": c["function"]["arguments"]})
        elif role == "tool":
            items.append({"type": "function_call_output", "call_id": m["tool_call_id"], "output": m["content"]})
        else:
            items.append({"role": role, "content": m["content"]})
    # The system prompt stays an input message, as in chat completions: the front desk
    # speaks first, so the opening call has nothing else, and Responses rejects empty input.
    return {
        "input": items,
        "tools": [{"type": "function", "strict": False, **t["function"]} for t in tools],
        # Stateless: reasoning comes back encrypted and is replayed on the next call.
        "store": False,
        "include": ["reasoning.encrypted_content"],
    }


def parse_response(response: dict[str, Any]) -> dict[str, Any]:
    """Responses API result -> the loop's reply {content, tool_calls, responses_output}."""
    output = response.get("output") or []
    text = "".join(
        part.get("text", "")
        for item in output if item.get("type") == "message"
        for part in item.get("content") or [] if part.get("type") == "output_text"
    )
    calls = []
    for item in output:
        if item.get("type") == "function_call":
            try:
                args = json.loads(item.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {"_raw": item.get("arguments")}
            calls.append({"id": item.get("call_id") or item.get("id"), "name": item.get("name"), "arguments": args})
    replay = [{k: v for k, v in item.items() if v is not None and k != "status"} for item in output]
    return {"content": text, "tool_calls": calls, "responses_output": replay}
