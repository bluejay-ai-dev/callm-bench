"""Conjunctive MICOL verdict plus the shaped RL reward for one episode (checks in grader.py)."""

from __future__ import annotations

from typing import Any

from . import grader as vt

# Handoff shaping: discount-factor decay in the signed hop delta, the standard
# RL length penalty (gamma^t). Applied only when tools AND state both pass —
# a proven-correct outcome lets route length speak for itself; an unproven one
# falls back to strict in-order matching so shortcuts earn nothing.
HANDOFF_GAMMA = 0.85
HANDOFF_BONUS_CAP = 1.25  # one saved hop ~ 1/0.85 = 1.18; cap keeps it bounded
FORBIDDEN_EXTRA_FACTOR = 0.5


def handoff_reward(
    expected_hops: int,
    actual_hops: int,
    strict_score: float,
    *,
    outcome_proven: bool,
) -> float:
    """Shaped handoff component in [0, HANDOFF_BONUS_CAP]."""
    if not outcome_proven:
        return strict_score
    delta = actual_hops - expected_hops
    return min(HANDOFF_GAMMA ** delta, HANDOFF_BONUS_CAP)


def shaped_components(
    tools: dict[str, Any], handoffs: dict[str, Any], state: dict[str, Any]
) -> dict[str, float]:
    r_tool = float(tools["score"])
    if tools.get("extra"):
        r_tool *= FORBIDDEN_EXTRA_FACTOR
    r_state = 1.0 if state["passed"] else 0.0
    r_handoff = handoff_reward(
        len(handoffs.get("expected") or []),
        len(handoffs.get("actual") or []),
        float(handoffs["score"]),
        outcome_proven=bool(tools["passed"] and state["passed"]),
    )
    return {
        "tool": r_tool,
        "handoff": r_handoff,
        "state": r_state,
        "shaped": (r_tool + r_handoff + r_state) / 3.0,
    }


def score(industry: str, task: dict[str, Any], episode_result: dict[str, Any]) -> dict[str, Any]:
    """Strict benchmark verdict (`conjunctive`) plus the RL-shaped reward (`shaped`)."""
    trace = episode_result["trace"]
    schemas = vt.load_tool_schemas(industry)

    tools = vt.tool_call_adherence(
        task.get("exp_tool_calls") or [], trace, schemas, industry=industry
    )
    names = [c["name"] for c in trace]
    handoffs = vt.handoff_adherence(
        vt.expected_handoff_path(task), vt.actual_handoffs(names, industry)
    )
    expected_state = vt.expected_state(task)
    if expected_state is None:
        state = {"passed": True, "verdict": "no_expected_state"}
    else:
        ok = vt.office_states_match(expected_state, episode_result["final_state"], industry)
        state = {"passed": bool(ok), "verdict": "match" if ok else "mismatch"}

    passed = bool(tools["passed"] and handoffs["passed"] and state["passed"])
    # RL tool component: prescribed transfers live in exp_tool_calls too, which
    # would veto the shorter-route bonus — judge tools on non-handoff calls only.
    handoff_names = vt.handoff_tools_for(industry)
    non_handoff_expected = [
        c for c in (task.get("exp_tool_calls") or [])
        if str((c or {}).get("name") or "") not in handoff_names
    ]
    tools_rl = vt.tool_call_adherence(non_handoff_expected, trace, schemas, industry=industry)
    rewards = shaped_components(tools_rl, handoffs, state)
    return {
        "task": task.get("_case_key") or task.get("task_name"),
        "industry": industry,
        "passed": passed,
        "conjunctive": 1.0 if passed else 0.0,
        "shaped": rewards["shaped"],
        "tool_reward": rewards["tool"],
        "handoff_reward": rewards["handoff"],
        "state_reward": rewards["state"],
        "components": {
            "tool_adherence": tools,
            "handoff_adherence": handoffs,
            "state_adherence": state,
        },
    }


def reward_file(scored: dict[str, Any]) -> dict[str, float]:
    """Flat numeric reward record. `reward` is the MICOL metric (conjunctive)."""
    return {
        "reward": scored["conjunctive"],
        "shaped": scored["shaped"],
        "tool_reward": scored["tool_reward"],
        "handoff_reward": scored["handoff_reward"],
        "state_reward": scored["state_reward"],
    }
