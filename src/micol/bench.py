"""Industry packs and tasks under `industries/<name>/` in this repo."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
INDUSTRIES = REPO_ROOT / "industries"

_TODAY_RE = re.compile(r'^TODAY\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def industry_dir(industry: str) -> Path:
    d = INDUSTRIES / industry
    if not d.is_dir():
        raise SystemExit(f"unknown industry {industry!r} under {INDUSTRIES}")
    return d


@lru_cache(maxsize=None)
def clock_line(industry: str) -> str:
    """The pack's pinned calendar (TODAY in its tool_server.py), appended to every agent prompt.

    MICOL_TODAY=YYYY-MM-DD overrides; MICOL_TODAY=wall uses the real date.
    """
    override = os.environ.get("MICOL_TODAY", "").strip()
    if override == "wall":
        d = date.today()
    elif override:
        d = date.fromisoformat(override.split("T", 1)[0])
    else:
        match = _TODAY_RE.search((industry_dir(industry) / "tool_server.py").read_text())
        d = date.fromisoformat(match.group(1).split("T", 1)[0]) if match else date.today()
    return f"Today is {d.strftime('%A')}, {d.strftime('%B')} {d.day}, {d.year}."


def variant_dir(industry: str, variant: str | None) -> Path | None:
    """`variants/<name>/` overlay: a file there replaces the pack file at the same relative path."""
    if not variant:
        return None
    d = industry_dir(industry) / "variants" / variant
    if not d.is_dir():
        raise SystemExit(f"unknown environment variant {variant!r} in industry {industry!r}")
    return d


def pack_file(industry: str, rel: str, variant: str | None = None) -> Path:
    v = variant_dir(industry, variant)
    if v is not None and (v / rel).is_file():
        return v / rel
    return industry_dir(industry) / rel


def task_variant(task: dict[str, Any]) -> str | None:
    return (task.get("metadata") or {}).get("env_variant")


@lru_cache(maxsize=None)
def load_blueprint(industry: str, variant: str | None = None) -> dict[str, Any]:
    """{start, agents: {name: {instructions, tools}}, catalog: {tool: spec}}."""
    blueprint = json.loads(pack_file(industry, "agent_blueprint.json", variant).read_text())
    catalog = {t["name"]: t for t in json.loads(pack_file(industry, "tools.json", variant).read_text())["tools"]}
    agents = {
        entry["name"]: {
            "name": entry["name"],
            "instructions": pack_file(industry, entry["system_prompt"], variant).read_text(),
            "tools": entry["tools"],
        }
        for entry in blueprint["agents"]
    }
    return {
        "industry": industry,
        "variant": variant,
        "start": blueprint["agents"][0]["name"],
        "agents": agents,
        "catalog": catalog,
    }


def list_tasks(industry: str) -> list[str]:
    tasks = industry_dir(industry) / "tasks"
    return sorted(p.name for p in tasks.iterdir() if (p / "task.json").is_file())


def load_task(industry: str, case_key: str) -> dict[str, Any]:
    path = industry_dir(industry) / "tasks" / case_key / "task.json"
    if not path.is_file():
        raise SystemExit(f"no task {case_key!r} in industry {industry!r}")
    task = json.loads(path.read_text())
    if task.get("task_id") != case_key:
        raise SystemExit(f"{path}: task_id {task.get('task_id')!r} must equal its folder name")
    task["_case_key"] = case_key
    return task


def task_tag(task: dict[str, Any]) -> str:
    """Readable bucket from metadata, e.g. C3-M, or P-C3-M for a private task."""
    meta = task.get("metadata") or {}
    diff = str(meta.get("difficulty") or "?")[:1].upper()
    prefix = "P-" if meta.get("split") == "private" else ""
    return f"{prefix}{meta.get('category') or '?'}-{diff}"


def tool_names(industry: str) -> set[str]:
    return set(load_blueprint(industry)["catalog"])
