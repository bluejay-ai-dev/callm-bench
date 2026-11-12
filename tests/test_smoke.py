"""Offline end-to-end checks against the real industry tool server and verifier.

No network LLM calls — FakeChat scripts both sides. These fail if the shared
turn loop, the Session (DAG state, tool scoping, prompt swaps), the tool
contract, the oracle, or the verifier wiring breaks.
"""

from __future__ import annotations

import asyncio
import copy

import pytest

from callm import bench, verify
from callm.env import Session, ToolServers, oracle_replay
from callm.llm import FakeChat
from callm.loop import ChatPolicy, LocalEnv, run_episode

INDUSTRY = "legal"
CASE = "lg-xskw"  # Conflict unclear, Harlow Properties

AGENT_SCRIPT = [
    {"content": "Thank you for calling Halverson and Reed. How can I help you today?"},
    {"content": "I'm sorry to hear that. May I have your full name and a callback number?"},
    {"tool_calls": [{"name": "lookup_caller",
                     "arguments": {"full_name": "Bernice Tolliver", "phone": "559-555-0208"}}]},
    {"tool_calls": [{"name": "transfer_to_screening", "arguments": {}}]},
    {"tool_calls": [{"name": "check_conflict", "arguments": {"opposing_party": "Harlow Properties"}}]},
    {"tool_calls": [{"name": "transfer_to_intake", "arguments": {}}]},
    {"tool_calls": [{"name": "record_intake", "arguments": {
        "practice_area": "premises_liability", "state": "CA", "incident_date": "2026-01-18",
        "summary": "Slipped on ice outside apartment and broke wrist; Harlow Properties."}}]},
    {"tool_calls": [{"name": "escalate_to_human", "arguments": {"reason_code": "conflict_review"}}]},
    {"content": "I've recorded your intake. A person will review the conflict and take it from here."},
]

USER_SCRIPT = [
    {"content": "I slipped on ice outside my apartment and broke my wrist."},
    {"content": "Bernice Tolliver, 559-555-0208."},
    {"content": "Okay, thank you. [HANGUP]"},
]


@pytest.fixture(scope="module")
def servers():
    s = ToolServers()
    yield s
    s.stop_all()


@pytest.fixture(scope="module")
def episode(servers):
    session = Session(INDUSTRY, CASE, servers.get(INDUSTRY), FakeChat(copy.deepcopy(USER_SCRIPT)))
    messages = asyncio.run(run_episode(ChatPolicy(FakeChat(copy.deepcopy(AGENT_SCRIPT))), LocalEnv(session)))
    result, scored = session.score()
    session.close()
    return session, messages, result, scored


def test_episode_pass(episode):
    _, _, result, s = episode
    # escalate_to_human is a session tool: the front desk hangs up after it fires
    assert result["ended_by"] == "agent"
    for part in ("tool_adherence", "handoff_adherence", "state_adherence"):
        assert s["components"][part]["passed"], s["components"][part]
    assert s["passed"] and s["conjunctive"] == 1.0
    assert verify.reward_file(s)["reward"] == 1.0


def test_handoff_swaps_prompt_and_tools(episode):
    session, _, result, _ = episode
    swaps = result["system_prompt_swaps"]
    assert [s["agent"] for s in swaps] == ["reception", "screening", "intake"]
    assert swaps[1]["after_tool_call"] == 2  # lookup_caller, transfer_to_screening
    assert swaps[0]["system_prompt"] != swaps[1]["system_prompt"]
    # tools before the hop ran under reception, after it under screening
    agents = {c["name"]: c["agent"] for c in result["trace"]}
    assert agents["lookup_caller"] == "reception"
    assert agents["check_conflict"] == "screening"


def test_close_deletes_call_db_after_snapshot(episode):
    session, _, result, s = episode
    assert result["final_state"]["escalations"]  # snapshot taken before close
    assert s["components"]["state_adherence"]["passed"]
    db = session.episode.server.call_db(session.episode.call_id)
    assert not db.exists()
    assert not db.with_name(db.name + "-wal").exists()
    with pytest.raises(RuntimeError):
        session.episode.final_state()


def test_expected_refusal_code_is_enforced(servers):
    # cs-2ayp (second price match on the same soundbar): quoting Halcyon before Rivertide succeeds instead of being refused
    # as a second match; every call still matches the key by name and arguments.
    session = Session("customer-support", "cs-2ayp", servers.get("customer-support"))
    halo = {"order_number": "KE-4495108", "sku": "SKU-AUD-7720", "competitor_price": 479.99}
    try:
        for name, args in [
            ("transfer_to_verification", {}),
            ("identify_customer", {"full_name": "Felix Moreau", "phone": "541-555-0108"}),
            ("verify_identity", {"postal_code": "94612", "card_last4": "3390"}),
            ("get_customer_summary", {}),
            ("transfer_to_orders", {}),
            ("get_order", {"order_number": "KE-4495108"}),
            ("quote_price_match", {**halo, "competitor": "Halcyon Mart"}),
            ("quote_price_match", {**halo, "competitor": "Rivertide"}),
            ("confirm_price_match", {"confirmation_token": "KE-PM-2286"}),
        ]:
            session.call_tool(name, args)
        _, scored = session.score()
    finally:
        session.close()
    assert scored["components"]["state_adherence"]["passed"]
    assert scored["components"]["tool_adherence"]["missing"] == ["quote_price_match"]
    assert not scored["passed"]


def test_tool_scoping_refuses_foreign_tools(servers):
    session = Session(INDUSTRY, CASE, servers.get(INDUSTRY))
    try:
        refused = session.call_tool("check_conflict", {"opposing_party": "Apex Build"})
        assert refused["error_code"] == "UNKNOWN_TOOL"  # reception does not own it
    finally:
        session.close()


def test_verifier_catches_missing_tool(episode):
    session, _, result, _ = episode
    broken = copy.deepcopy(result)
    broken["trace"] = [c for c in broken["trace"] if c["name"] != "check_conflict"]
    s = verify.score(INDUSTRY, session.task, broken)
    assert not s["components"]["tool_adherence"]["passed"]
    assert not s["passed"]


def test_verifier_catches_wrong_state(episode):
    session, _, result, _ = episode
    broken = copy.deepcopy(result)
    broken["final_state"]["escalations"] = []
    s = verify.score(INDUSTRY, session.task, broken)
    assert not s["components"]["state_adherence"]["passed"]
    assert not s["passed"]


# Every answer key must replay to its own expected DB: a failure means the
# expected calls and the expected end state disagree.
@pytest.mark.parametrize(
    "industry,case",
    [(i, k) for i in ("healthcare", "legal", "customer-support") for k in bench.list_tasks(i)],
)
def test_oracle_replays_to_pass(servers, industry, case):
    session = Session(industry, case, servers.for_task(industry, case))
    try:
        oracle_replay(session)
        _, scored = session.score()
    finally:
        session.close()
    assert scored["passed"], scored["components"]


def test_every_task_is_tagged():
    # the original 180 are mivas-v1; every other task names where it came from
    for industry in ("healthcare", "legal", "customer-support"):
        for case in bench.list_tasks(industry):
            meta = bench.load_task(industry, case).get("metadata") or {}
            tags = meta.get("tags")
            assert tags and isinstance(tags, list), (industry, case)
            assert ("mivas-v1" in tags) == (meta.get("split") == "public"), (industry, case, tags)


def test_asr_channel_delivers_heard_segments(servers):
    # SAID stays with the caller; the agent gets HEARD, one ` || ` segment per turn,
    # and an empty HEARD is never handed to the agent.
    caller = FakeChat([
        {"content": "SAID: Caroline Delaney, seven one eight, five five five, zero one seven seven.\n"
                    "HEARD: Caroline Delaney. || 718-555-0717"},
        {"content": "SAID: Yes.\nHEARD:"},
        {"content": "SAID: Thanks, bye. [HANGUP]\nHEARD: Thanks, bye."},
    ])
    session = Session(INDUSTRY, CASE, servers.get(INDUSTRY), caller, asr_profile="stt-simulated-gpt-6.1-sol",
                      asr_draws=False)
    try:
        assert "HEARD:" in session.user.messages[0]["content"]
        assert session.end_turn("Name and number?")["text"] == "Caroline Delaney."
        assert session.end_turn("Got it.")["text"] == "718-555-0717"
        # an empty HEARD never reaches the agent: the caller hears silence and speaks again
        assert session.end_turn("Is that right?") == {"text": "Thanks, bye.", "hangup": True, "done": True}
        assert session.user.messages[3]["content"] == "Got it. Is that right?"
        assert session.user.messages[5]["content"] == "(silence)"
        dropped = [t for t in session.transcript if t.get("dropped")]
        assert [t["said"] for t in dropped] == ["Yes."] and dropped[0]["text"] == ""
        said = [t["said"] for t in session.transcript if "said" in t]
        assert said[0].endswith("zero one seven seven.") and said[-1] == "Thanks, bye."
    finally:
        session.close()


def test_recognizer_draws_match_profile_rates_and_repeat():
    from callm.usersim import draw, load_rates
    rates = load_rates("stt-simulated-gpt-6.1-sol")
    draws = [draw(rates, f"0|legal|lg-x|{i}") for i in range(40000)]
    share = lambda o: sum(d["outcome"] == o for d in draws) / len(draws)  # noqa: E731
    assert abs(share("none") - rates["rate_dropped"]) < 0.005
    assert abs(share("substantial") - rates["rate_major"]) < 0.005
    assert abs(sum(d["split"] for d in draws) / len(draws) - rates["rate_split"]) < 0.005
    assert draw(rates, "0|legal|lg-x|7") == draws[7]


def test_enforce_applies_mechanical_draws():
    from callm.usersim import enforce
    base = {"outcome": "minor", "split": False, "final_punctuation": True, "lowercase": False}
    assert enforce("Hello there.", dict(base, outcome="none")) == ""
    assert enforce("Hi. || I need help.", base) == "Hi. I need help."
    assert enforce("Hi, I need help.", dict(base, split=True)) == "Hi, || I need help."
    assert enforce("Hi, I need help.", dict(base, lowercase=True, final_punctuation=False)) == "hi, i need help"


def test_session_hands_the_caller_its_draw(servers):
    from callm.usersim import draw, draw_line, enforce, load_rates
    caller = FakeChat([{"content": "SAID: Caroline Delaney.\nHEARD: Caroline Delaney."}])
    session = Session(INDUSTRY, CASE, servers.get(INDUSTRY), caller, asr_profile="stt-simulated-gpt-6.1-sol",
                      attempt=3, channel_seed=5)
    try:
        expected = draw(load_rates("stt-simulated-gpt-6.1-sol"), f"5|{INDUSTRY}|{CASE}|3|0")
        out = session.end_turn("Your name?")
        assert session.user.messages[1]["content"].endswith(draw_line(expected))
        assert out["text"] == enforce("Caroline Delaney.", expected)
        assert session.transcript[-1]["draw"] == expected
    finally:
        session.close()
