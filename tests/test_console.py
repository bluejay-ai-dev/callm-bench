"""Console API end to end on an oracle run (no model, no Gym)."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from micol.console import api, runs


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(runs, "RUNS", tmp_path)
    with TestClient(api.app) as c:
        yield c


def test_oracle_run_through_the_api(client):
    tasks = [{"industry": "legal", "case_key": "lg-xskw"}, {"industry": "customer-support", "case_key": "cs-2ayp"}]
    run = client.post("/api/runs", json={"kind": "oracle", "tasks": tasks, "repeats": 2}).json()
    detail: dict[str, Any] = {}
    for _ in range(100):
        detail = client.get(f"/api/runs/{run['id']}").json()
        if detail["status"] not in runs.ACTIVE:
            break
        time.sleep(0.1)
    assert detail["status"] == "done", detail
    assert detail["summary"]["all"] == {**detail["summary"]["all"], "n": 4, "passed": 4, "tasks": 2, "k": 2,
                                        "pass_any": 2, "pass_all": 2}
    assert sorted((r["case_key"], r["attempt"]) for r in detail["rows"]) == [
        ("cs-2ayp", 0), ("cs-2ayp", 1), ("lg-xskw", 0), ("lg-xskw", 1)]

    view = client.get(f"/api/runs/{run['id']}/rollouts/legal/lg-xskw/1").json()
    assert view["attempt"] == 1 and [a["attempt"] for a in view["attempts"]] == [0, 1]
    kinds = [e["kind"] for e in view["timeline"]]
    assert kinds.count("handoff") == 2 and kinds.index("handoff") == 2  # after lookup_caller, transfer_to_screening
    assert [r["status"] for r in view["grading"]["tool_rows"]] == ["match"] * 6
    assert {t["table"] for t in view["grading"]["db_tables"]} >= {"escalations", "intakes"}

    refused = client.get(f"/api/runs/{run['id']}/rollouts/customer-support/cs-2ayp/0").json()
    assert any(e.get("error_code") == "PRICE_MATCH_ALREADY_USED" for e in refused["timeline"])

    assert client.get(f"/api/runs/{run['id']}/rollouts/legal/lg-xskw/2").status_code == 404
    history = client.get("/api/tasks/legal/lg-xskw").json()["history"]
    assert [len(h["attempts"]) for h in history] == [2]

    assert client.delete(f"/api/runs/{run['id']}").json() == {"deleted": True}
    assert client.get(f"/api/runs/{run['id']}").status_code == 404


def test_bad_requests(client):
    assert client.post("/api/runs", json={"kind": "oracle", "tasks": []}).status_code == 400
    assert client.post("/api/runs", json={"kind": "gym", "config": "nope", "tasks": [{"industry": "legal", "case_key": "lg-xskw"}]}).status_code == 400
    assert client.get("/api/tasks/legal/NOPE").status_code == 404
