"""freeze: a new task's expected end state comes from replaying its own answer key."""

from __future__ import annotations

import json
import shutil

import pytest

from micol import bench
from micol.env import ToolServers, freeze
from micol.llm import add_usage, new_usage

INDUSTRY, SOURCE, DRAFT = "legal", "lg-xskw", "lg-zzzz"


@pytest.fixture
def draft():
    src = bench.industry_dir(INDUSTRY) / "tasks" / SOURCE
    dst = src.parent / DRAFT
    shutil.copytree(src, dst)
    task = json.loads((dst / "task.json").read_text())
    expected_state = task.pop("exp_db_state")
    task["task_id"] = DRAFT
    task["metadata"]["split"] = "draft"
    (dst / "task.json").write_text(json.dumps(task))
    servers = ToolServers()
    yield dst, expected_state, servers
    servers.stop_all()
    shutil.rmtree(dst)


def test_freeze_writes_the_replayed_end_state(draft):
    dst, expected_state, servers = draft
    assert freeze(INDUSTRY, DRAFT, servers) == []
    frozen = json.loads((dst / "task.json").read_text())["exp_db_state"]
    assert frozen.keys() == expected_state.keys()
    assert frozen["escalations"] == expected_state["escalations"]


def test_freeze_rejects_a_key_whose_call_fails(draft):
    dst, _, servers = draft
    task = json.loads((dst / "task.json").read_text())
    call = next(c for c in task["exp_tool_calls"] if c["name"] == "check_conflict")
    call["parameters"] = {}
    (dst / "task.json").write_text(json.dumps(task))
    problems = freeze(INDUSTRY, DRAFT, servers)
    assert any("check_conflict" in p for p in problems)
    assert "exp_db_state" not in json.loads((dst / "task.json").read_text())


def test_usage_adds_both_api_shapes():
    total = new_usage()
    add_usage(total, {"prompt_tokens": 10, "completion_tokens": 3, "prompt_tokens_details": {"cached_tokens": 4}})
    add_usage(total, {"input_tokens": 7, "output_tokens": 2, "input_tokens_details": {"cached_tokens": 1}})
    add_usage(total, None)
    assert total == {"input": 17, "cached": 5, "output": 5, "calls": 2}
