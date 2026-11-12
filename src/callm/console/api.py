"""CALLM console: HTTP API over runs, tasks, and the Gym stack, plus the built UI at /.

    callm ui            # http://127.0.0.1:8765
"""

from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from typing import Any, Literal

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from callm import bench
from callm.console import runs, views

INDUSTRIES = ("healthcare", "legal", "customer-support")
UI_DIST = bench.REPO_ROOT / "ui" / "dist"
EXAMPLE = bench.REPO_ROOT / "resources_servers" / "callm" / "data" / "example.jsonl"


@asynccontextmanager
async def lifespan(_: FastAPI):
    runs.mark_interrupted()
    yield
    if runs.STACK.proc is not None:  # only a stack this process started; `ray stop` is host-wide
        runs.STACK.stop()
    runs.TOOL_SERVERS.stop_all()


app = FastAPI(title="CALLM console", lifespan=lifespan)


def _run_or_404(run_id: str) -> dict[str, Any]:
    try:
        return runs.read_meta(run_id)
    except KeyError:
        raise HTTPException(404, f"no run {run_id!r}") from None


def _task_or_404(industry: str, case_key: str) -> dict[str, Any]:
    if industry not in INDUSTRIES:
        raise HTTPException(404, f"no industry {industry!r}")
    try:
        return bench.load_task(industry, case_key)
    except SystemExit as exc:
        raise HTTPException(404, str(exc)) from None


# ---------------------------------------------------------------- environment

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "stack": runs.STACK.status(),
        "queue": {"current": runs.QUEUE.current, "pending": list(runs.QUEUE.pending)},
    }


@app.post("/api/stack/stop")
def stop_stack() -> dict[str, Any]:
    if runs.QUEUE.current and runs.read_meta(runs.QUEUE.current)["kind"] == "gym":
        raise HTTPException(409, "a Gym run is using the stack; cancel it first")
    runs.STACK.stop()
    return runs.STACK.status()


@app.get("/api/stack/log")
def stack_log(lines: int = 200) -> dict[str, str]:
    return {"log": runs.tail(runs.STACK.log, lines)}


@app.get("/api/configs")
def configs() -> list[dict[str, Any]]:
    out = []
    for path in sorted(runs.CONFIGS.glob("*.yaml")):
        text = path.read_text()
        doc = yaml.safe_load(text) or {}

        def model(role: str) -> dict[str, Any]:
            spec = (doc.get(role) or {}).get("responses_api_models") or {}
            server = next(iter(spec.values()), {}) if spec else {}
            return {"model": server.get("openai_model") or server.get("model"),
                    "base_url": server.get("openai_base_url") or server.get("base_url")}

        out.append({
            "name": path.stem,
            "description": " ".join(line.lstrip("# ").strip() for line in text.splitlines()[:2] if line.startswith("#")),
            "policy": model("policy_model"), "user": model("user_model"),
            "keys": sorted(set(re.findall(r"oc\.env:(\w+)", text))),
        })
    return out


# ---------------------------------------------------------------- tasks

@app.get("/api/tasks")
def tasks() -> dict[str, Any]:
    rows = []
    for industry in INDUSTRIES:
        for key in bench.list_tasks(industry):
            t = bench.load_task(industry, key)
            meta = t.get("metadata") or {}
            rows.append({
                "industry": industry, "case_key": key, "name": t.get("task_name"), "tag": bench.task_tag(t),
                "category": meta.get("category"), "difficulty": meta.get("difficulty"),
                "calls": len(t.get("exp_tool_calls") or []), "handoffs": len(t.get("exp_handoff_path") or []),
                "split": meta.get("split"),
                "tags": meta.get("tags") or [],
            })
    order = {i: n for n, i in enumerate(INDUSTRIES)}
    rows.sort(key=lambda r: (order[r["industry"]], r["split"] == "private", r["tag"], r["name"] or ""))
    example = [line for line in EXAMPLE.read_text().splitlines() if line.strip()] if EXAMPLE.is_file() else []
    return {"tasks": rows, "presets": {"example": [json.loads(line) for line in example]}}


@app.get("/api/tasks/{industry}/{case_key}")
def task(industry: str, case_key: str) -> dict[str, Any]:
    t = _task_or_404(industry, case_key)
    bp = bench.load_blueprint(industry, bench.task_variant(t))
    history = []
    for meta in runs.list_runs():
        attempts = views.attempts_of(runs.rollouts(meta["id"]), industry, case_key)
        if attempts:
            history.append({"run": {k: meta.get(k) for k in ("id", "label", "kind", "config", "created_at")},
                            "attempts": [views.row_brief(r) for r in attempts]})
    return {
        "task": {k: v for k, v in t.items() if k != "_case_key"},
        "tag": bench.task_tag(t),
        "agents": [{"name": a["name"], "tools": [x["name"] for x in a["tools"]]} for a in bp["agents"].values()],
        "start": bp["start"],
        "history": history,
    }


@app.post("/api/tasks/{industry}/{case_key}/oracle")
def task_oracle(industry: str, case_key: str) -> dict[str, Any]:
    t = _task_or_404(industry, case_key)
    row = runs.oracle_record({"industry": industry, "case_key": case_key})
    return {"rollout": row, "timeline": views.timeline(row), "grading": views.grading(industry, t, row)}


# ---------------------------------------------------------------- runs

class TaskRef(BaseModel):
    industry: str
    case_key: str


class NewRun(BaseModel):
    kind: Literal["gym", "oracle"]
    tasks: list[TaskRef]
    config: str | None = None
    concurrency: int = Field(default=32, ge=1, le=256)
    repeats: int = Field(default=1, ge=1, le=20)
    label: str = ""
    caller: str | None = None
    source: dict[str, Any] | None = None


_SUMMARIES: dict[str, tuple[tuple[int, int], dict[str, Any]]] = {}


def _with_summary(meta: dict[str, Any]) -> dict[str, Any]:
    # The runs list polls every few seconds; re-parse a run's rollouts only when the file changed.
    path = runs.run_dir(meta["id"]) / "rollouts.jsonl"
    st = path.stat() if path.is_file() else None
    key = (st.st_mtime_ns, st.st_size) if st else (0, 0)
    cached = _SUMMARIES.get(meta["id"])
    if cached is None or cached[0] != key:
        rows = runs.rollouts(meta["id"])
        cached = (key, {"done": len(rows), "summary": views.summarize(rows)})
        _SUMMARIES[meta["id"]] = cached
    return {**meta, **cached[1]}


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    return [_with_summary(m) for m in runs.list_runs()]


@app.post("/api/runs")
def create_run(body: NewRun) -> dict[str, Any]:
    try:
        return runs.create_run(body.kind, [t.model_dump() for t in body.tasks], config=body.config,
                               concurrency=body.concurrency, label=body.label, repeats=body.repeats,
                               caller=body.caller, source=body.source)
    except (ValueError, SystemExit) as exc:
        raise HTTPException(400, str(exc)) from None


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    meta = _run_or_404(run_id)
    rows = runs.rollouts(run_id)
    return {**meta, "done": len(rows), "summary": views.summarize(rows), "rows": [views.row_brief(r) for r in rows]}


@app.get("/api/runs/{run_id}/log")
def run_log(run_id: str, lines: int = 200) -> dict[str, str]:
    meta = _run_or_404(run_id)
    if meta["kind"] == "gym" and meta["status"] == "starting":
        return {"log": runs.tail(runs.STACK.log, lines)}
    return {"log": runs.tail(runs.run_dir(run_id) / "eval.log", lines)}


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, Any]:
    _run_or_404(run_id)
    try:
        runs.QUEUE.cancel_run(run_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return runs.read_meta(run_id)


@app.post("/api/runs/{run_id}/rerun")
def rerun(run_id: str) -> dict[str, Any]:
    meta = _run_or_404(run_id)
    rows = (runs.run_dir(run_id) / "input.jsonl").read_text().splitlines()
    refs = [json.loads(line) for line in rows if line.strip()]
    try:
        return runs.create_run(meta["kind"], [{"industry": r["industry"], "case_key": r["case_key"]} for r in refs],
                               config=meta.get("config"), concurrency=meta.get("concurrency") or 32,
                               label=f"rerun of {meta.get('label') or run_id}", repeats=meta.get("repeats") or 1,
                               caller=meta.get("caller"), source=meta.get("source"))
    except (ValueError, SystemExit) as exc:
        raise HTTPException(400, str(exc)) from None


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str) -> dict[str, bool]:
    _run_or_404(run_id)
    try:
        runs.delete_run(run_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"deleted": True}


@app.get("/api/runs/{run_id}/rollouts/{industry}/{case_key}/{attempt}")
def rollout(run_id: str, industry: str, case_key: str, attempt: int) -> dict[str, Any]:
    _run_or_404(run_id)
    t = _task_or_404(industry, case_key)
    attempts = views.attempts_of(runs.rollouts(run_id), industry, case_key)
    row = next((r for r in attempts if views.attempt(r) == attempt), None)
    if row is None:
        raise HTTPException(404, f"no attempt {attempt} for that task in this run (yet)")
    keep = ("industry", "case_key", "category", "difficulty", "reward", "conjunctive", "shaped", "tool_reward",
            "handoff_reward", "state_reward", "ended_by", "failure_kind", "failure_reason", "system_prompt_swaps",
            "final_state", "trace", "transcript")
    return {"rollout": {k: row.get(k) for k in keep}, "timeline": views.timeline(row),
            "grading": views.grading(industry, t, row), "task": {k: v for k, v in t.items() if k != "_case_key"},
            "tag": bench.task_tag(t),
            "attempt": attempt, "attempts": [views.row_brief(r) for r in attempts]}


@app.get("/api/compare")
def compare(ids: str) -> dict[str, Any]:
    metas = [_run_or_404(i) for i in ids.split(",") if i]
    cells: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for meta in metas:
        for r in sorted(runs.rollouts(meta["id"]), key=views.attempt):
            cells.setdefault(f"{r['industry']}/{r['case_key']}", {}).setdefault(meta["id"], []).append(views.row_brief(r))
    return {"runs": [_with_summary(m) for m in metas],
            "tasks": sorted(({"key": k, "industry": k.split("/")[0], "case_key": k.split("/")[1],
                              "tag": next(iter(v.values()))[0]["tag"], "title": next(iter(v.values()))[0]["title"],
                              "cells": v} for k, v in cells.items()),
                            key=lambda t: (t["industry"], t["tag"], t["title"]))}


# ---------------------------------------------------------------- UI

if UI_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404, "no such API route")
        return FileResponse(UI_DIST / "index.html")
