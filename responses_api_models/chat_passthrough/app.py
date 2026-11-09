"""Gym model server that forwards /v1/chat/completions to an OpenAI-compatible endpoint verbatim.

Gym's stock `openai_model` validates chat requests against a strict schema, which strips
provider extensions the provider requires back on the next turn. Gemini 3 is the case that
needs this: every tool call carries `extra_content.google.thought_signature`, and a follow-up
turn without it is rejected ("Function call is missing a thought_signature").
Everything else (`/v1/responses`, config, concurrency cap) is `openai_model` as shipped.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from aiohttp import ClientResponseError
from fastapi import Body, Request

from responses_api_models.openai_model.app import SimpleModelServer, SimpleModelServerConfig


RETRY_STATUSES = {408, 429, 500, 502, 503, 504, 520, 529}


class ChatPassthroughModelServerConfig(SimpleModelServerConfig):
    # Gemini rejects a request with only system messages ("contents is not specified"), which
    # is every agent's opening turn when the agent speaks first. When set, such a request gets
    # this one user turn appended; providers that accept system-only requests leave it unset.
    opening_user_message: str | None = None


class ChatPassthroughModelServer(SimpleModelServer):
    config: ChatPassthroughModelServerConfig  # pyright: ignore[reportIncompatibleVariableOverride]

    async def chat_completions_dispatch(self, request: Request, body: dict[str, Any] = Body()):  # pyright: ignore[reportIncompatibleMethodOverride]
        if body.get("stream") is True:
            return await super().chat_completions_dispatch(request, body)
        payload = self.config.extra_body | body
        payload["model"] = self.config.openai_model
        messages = payload.get("messages") or []
        if self.config.opening_user_message and all(m.get("role") in ("system", "developer") for m in messages):
            payload["messages"] = [*messages, {"role": "user", "content": self.config.opening_user_message}]
        # Gym retries 5xx only 3 times and never 529 (Anthropic "overloaded"); a lost call drops the rollout.
        for attempt in range(8):
            try:
                async with self._semaphore:
                    return await self._client.create_chat_completion(**payload)
            except ClientResponseError as e:
                if e.status not in RETRY_STATUSES or attempt == 7:
                    raise
            await asyncio.sleep(min(2**attempt, 60) * (1 + random.random()))


if __name__ == "__main__":
    ChatPassthroughModelServer.run_webserver()
