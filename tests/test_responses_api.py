"""Responses API policy path: request bodies Gym's model server accepts, replies the loop reads."""

from __future__ import annotations

from micol.llm import parse_response, responses_request
from micol.loop import assistant_message
from nemo_gym.openai_utils import NeMoGymResponseCreateParamsNonStreaming

TOOL = {"type": "function", "function": {"name": "lookup", "description": "d", "parameters": {"type": "object", "properties": {}}}}


def test_reply_round_trips_into_a_valid_request():
    reply = parse_response({"output": [
        {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "enc", "status": None},
        {"type": "function_call", "id": "fc_1", "call_id": "c1", "name": "lookup", "arguments": '{"q": 1}', "status": "completed"},
        {"type": "message", "id": "m1", "role": "assistant", "status": "completed",
         "content": [{"type": "output_text", "text": "One moment.", "annotations": []}]},
    ]})
    assert reply["content"] == "One moment."
    assert reply["tool_calls"] == [{"id": "c1", "name": "lookup", "arguments": {"q": 1}}]

    history = [{"role": "system", "content": "You are reception."}, {"role": "user", "content": "hi"},
               assistant_message(reply), {"role": "tool", "tool_call_id": "c1", "content": "{}"}]
    req = responses_request(history, [TOOL])
    NeMoGymResponseCreateParamsNonStreaming.model_validate(req)
    # system prompt first; reasoning is replayed with its tool call, then the tool result answers it
    assert [i.get("type", i.get("role")) for i in req["input"]] == [
        "system", "user", "reasoning", "function_call", "message", "function_call_output"]
    assert req["tools"][0]["name"] == "lookup" and req["store"] is False


def test_opening_call_has_input():
    req = responses_request([{"role": "system", "content": "Greet the caller."}], [TOOL])
    NeMoGymResponseCreateParamsNonStreaming.model_validate(req)
    assert req["input"] == [{"role": "system", "content": "Greet the caller."}]


def test_chat_tool_call_provider_state_round_trips():
    # Gemini 3 rejects a follow-up turn unless each tool call carries its thought_signature back.
    from micol.llm import parse_message
    sig = {"google": {"thought_signature": "SIG"}}
    reply = parse_message({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": "{}"}, "extra_content": sig}]})
    assert assistant_message(reply)["tool_calls"][0]["extra_content"] == sig
    plain = parse_message({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c2", "type": "function", "function": {"name": "lookup", "arguments": "{}"}}]})
    assert "extra_content" not in assistant_message(plain)["tool_calls"][0]
