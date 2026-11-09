"""Shaped-reward unit checks: gating, shorter-route bonus, longer-route decay."""

from __future__ import annotations

from micol.verify import (
    HANDOFF_BONUS_CAP,
    HANDOFF_GAMMA,
    handoff_reward,
    shaped_components,
)


def test_exact_path_full_credit():
    assert handoff_reward(2, 2, 0.5, outcome_proven=True) == 1.0


def test_shorter_route_bonus_when_proven():
    r = handoff_reward(2, 1, 0.0, outcome_proven=True)
    assert r == min(HANDOFF_GAMMA ** -1, HANDOFF_BONUS_CAP) > 1.0


def test_bonus_capped():
    assert handoff_reward(5, 0, 0.0, outcome_proven=True) == HANDOFF_BONUS_CAP


def test_longer_route_decays():
    r1 = handoff_reward(1, 2, 1.0, outcome_proven=True)
    r3 = handoff_reward(1, 4, 1.0, outcome_proven=True)
    assert r1 == HANDOFF_GAMMA and r3 == HANDOFF_GAMMA ** 3
    assert 0.0 < r3 < r1 < 1.0


def test_no_shortcut_credit_when_unproven():
    # tools or state failed: strict in-order score only, no route bonus
    assert handoff_reward(2, 1, 0.5, outcome_proven=False) == 0.5
    assert handoff_reward(2, 1, 0.0, outcome_proven=False) == 0.0


def _tools(passed=True, score=1.0, extra=()):
    return {"passed": passed, "score": score, "extra": list(extra)}


def _handoffs(expected, actual, score):
    return {"expected": expected, "actual": actual, "score": score, "passed": True}


def test_shaped_perfect_run_is_one():
    r = shaped_components(_tools(), _handoffs(["a"], ["a"], 1.0), {"passed": True})
    assert r["shaped"] == 1.0


def test_forbidden_extra_halves_tool_reward():
    r = shaped_components(
        _tools(passed=False, extra=["send_sms"]),
        _handoffs(["a"], ["a"], 1.0),
        {"passed": True},
    )
    assert r["tool"] == 0.5


def test_state_failure_gates_handoff_shaping():
    r = shaped_components(
        _tools(), _handoffs(["a", "b"], ["a"], 0.5), {"passed": False}
    )
    assert r["handoff"] == 0.5 and r["state"] == 0.0
