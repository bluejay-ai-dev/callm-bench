"""Phone-LLM bench report for one console run, computed from its rollouts alone.

Task metrics (pass^k, robustness drop against a clean run, pass by recognizer outcome,
misheard writes, clarifications, read-backs, speakability), LLM call metrics (tokens, cache,
context growth, reliability, tool-call validity, served model, cost), the caller channel's
realized rates against the profile's real targets, and any latency-pass summaries.
"""

from __future__ import annotations

import collections
import json
import random
import re
import statistics
from pathlib import Path
from typing import Any

from . import bench
from .channel import call_records, norm, pool, surface
from .latency import percentiles
from .usersim import PROFILES

ASK = re.compile(r"\b(repeat|again|confirm|spell|catch|sorry|say that|could you|is that)\b", re.I)
MARKDOWN = re.compile(r"(\*\*|__|^#{1,6} |^\s*[-*] |^\s*\d+\. |\|.+\|)", re.M)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
URL = re.compile(r"https?://|www\.", re.I)
LONG_TURN_WORDS = 50
DRAW_CLASS = {"correct": "exact", "minor": "minor", "substantial": "major", "clipped": "truncated", "none": "dropped"}
SPOKEN_WPM = 150


def _passed(row: dict[str, Any]) -> bool:
    return float(row.get("conjunctive", row.get("reward") or 0)) >= 1.0


def _by_task(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        out[(r["industry"], r["case_key"])].append(r)
    return out


def task_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tasks = _by_task(rows)
    k = max((len(v) for v in tasks.values()), default=0)
    comp = lambda name: sum(bool((r.get("components") or {}).get(name, {}).get("passed")) for r in rows) / max(1, len(rows))  # noqa: E731
    return {
        "episodes": len(rows), "tasks": len(tasks), "k": k,
        "pass_rate": sum(map(_passed, rows)) / max(1, len(rows)),
        "pass_at_k": sum(any(map(_passed, v)) for v in tasks.values()) / max(1, len(tasks)),
        "pass_hat_k": sum(all(map(_passed, v)) for v in tasks.values()) / max(1, len(tasks)),
        "tool_pass": comp("tool_adherence"), "handoff_pass": comp("handoff_adherence"), "state_pass": comp("state_adherence"),
        "errors": sum(bool(r.get("error")) for r in rows),
    }


def robustness_drop(clean: list[dict[str, Any]], noisy: list[dict[str, Any]], *, resamples: int = 1000) -> dict[str, Any]:
    """Clean minus profile pass rate, paired per task, bootstrap CI over tasks."""
    a, b = _by_task(clean), _by_task(noisy)
    diffs = [sum(map(_passed, a[t])) / len(a[t]) - sum(map(_passed, b[t])) / len(b[t]) for t in a.keys() & b.keys()]
    if not diffs:
        return {"paired_tasks": 0}
    rng = random.Random(0)
    boots = sorted(statistics.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(resamples))
    return {"paired_tasks": len(diffs), "drop": statistics.fmean(diffs),
            "ci95": [boots[int(0.025 * resamples)], boots[int(0.975 * resamples) - 1]]}


def _turns(row: dict[str, Any]) -> tuple[list[str], list[str], list[int]]:
    """Caller SAID utterances, all HEARD segments, and each SAID's transcript index."""
    said, heard, where = [], [], []
    for i, t in enumerate(row.get("transcript") or []):
        if t.get("role") == "customer" and "said" in t:
            said.append(t["said"]); where.append(i)
            heard.extend(t.get("heard_segments") or [])
    return said, heard, where


def _next_agent(transcript: list[dict[str, Any]], i: int) -> str:
    for t in transcript[i + 1:]:
        if t.get("role") == "agent":
            return t.get("text") or ""
    return ""


def _caller_name(row: dict[str, Any]) -> str:
    try:
        return bench.load_task(row["industry"], row["case_key"]).get("customer_name") or ""
    except (Exception, SystemExit):  # bench exits on an unknown industry or task
        return ""


def _tool_catalog(row: dict[str, Any]) -> dict[str, Any]:
    try:
        variant = bench.task_variant(bench.load_task(row["industry"], row["case_key"]))
        tools = json.loads(bench.pack_file(row["industry"], "tools.json", variant).read_text())["tools"]
    except (Exception, SystemExit):  # bench exits on an unknown industry or task
        return {}
    return {t["name"]: t for t in tools}


def _db_digit_values(state: Any) -> set[str]:
    out: set[str] = set()

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, (str, int)):
            d = re.sub(r"\D", "", str(v))
            if len(d) >= 3:
                out.add(d)
    walk(state)
    return out


def channel_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    records, surfaces = [], []
    by_class: dict[str, list[bool]] = collections.defaultdict(list)
    misheard_eligible = misheard = clar_eligible = clarified = readback_eligible = readback = 0
    followed: dict[str, list[bool]] = collections.defaultdict(list)
    for row in rows:
        said, heard, where = _turns(row)
        if not said:
            continue
        recs = call_records(said, heard, _caller_name(row))
        transcript_rows = row.get("transcript") or []
        for r in recs:
            entry = transcript_rows[where[r["idx"]]]
            d = entry.get("draw")
            if d:
                # a blanked turn is checked directly: the aligner can credit a neighbour's words to it
                ok = not entry.get("heard_segments") if d["outcome"] == "none" else DRAW_CLASS[d["outcome"]] == r["cls"]
                followed[d["outcome"]].append(ok)
        records += recs
        surfaces.append(surface(heard))
        transcript = row.get("transcript") or []
        flags = {r["cls"] for r in recs} | {"split" for r in recs if r["split"]}
        flags |= {"digits_broken" for r in recs if r["digits"] is False} | {"name_broken" for r in recs if r["names"] is False}
        for f in flags:
            by_class[f].append(_passed(row))
        db_digits = _db_digit_values(row.get("final_state"))
        broke_digits = False
        for r in recs:
            reply = _next_agent(transcript, where[r["idx"]])
            if r["cls"] in ("dropped", "major", "truncated") or r["digits"] is False or r["names"] is False:
                clar_eligible += 1
                clarified += bool("?" in reply and ASK.search(reply))
            if r["digits"] is False:
                broke_digits = True
                said_d = "".join(w for w in norm(r["said"]) if w.isdigit())
                heard_d = "".join(w for w in norm(r["heard"]) if w.isdigit())
                reply_d = re.sub(r"\D", "", " ".join(w for w in norm(reply) if w.isdigit()))
                readback_eligible += 1
                readback += bool(heard_d and heard_d in reply_d)
                if heard_d in db_digits and said_d not in db_digits:
                    misheard += 1
        misheard_eligible += broke_digits
    rate = lambda a, b: a / b if b else None  # noqa: E731
    return {
        "realized": pool(records, surfaces) if records else None,
        "pass_by_outcome": {k: {"episodes": len(v), "pass_rate": sum(v) / len(v)} for k, v in sorted(by_class.items())},
        "misheard_write_rate": rate(misheard, misheard_eligible),
        "misheard_writes": misheard,
        "clarification_rate": rate(clarified, clar_eligible),
        "readback_rate": rate(readback, readback_eligible),
        # did the HEARD the caller wrote land in the class its draw asked for
        "draw_compliance": {k: {"turns": len(v), "followed": sum(v) / len(v)} for k, v in sorted(followed.items())},
    }


def speakability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    turns = [t.get("text") or "" for r in rows for t in r.get("transcript") or [] if t.get("role") == "agent"]
    n = max(1, len(turns))
    return {
        "agent_turns": len(turns),
        "markdown_rate": sum(bool(MARKDOWN.search(t)) for t in turns) / n,
        "emoji_or_url_rate": sum(bool(EMOJI.search(t) or URL.search(t)) for t in turns) / n,
        "over_50_words_rate": sum(len(t.split()) > LONG_TURN_WORDS for t in turns) / n,
        "words_per_turn": statistics.fmean(len(t.split()) for t in turns) if turns else None,
    }


def _tokens(usage: dict[str, Any] | None) -> dict[str, int]:
    u = usage or {}
    pin = u.get("prompt_tokens_details") or u.get("input_tokens_details") or {}
    pout = u.get("completion_tokens_details") or u.get("output_tokens_details") or {}
    return {"input": int(u.get("prompt_tokens") or u.get("input_tokens") or 0),
            "cached": int(pin.get("cached_tokens") or 0),
            "output": int(u.get("completion_tokens") or u.get("output_tokens") or 0),
            "reasoning": int(pout.get("reasoning_tokens") or 0)}


def llm_metrics(rows: list[dict[str, Any]], prices: dict[str, float] | None = None) -> dict[str, Any]:
    calls = [c for r in rows for c in r.get("policy_calls") or []]
    if not calls:
        return {"calls": 0}
    toks = [_tokens(c.get("usage")) for c in calls]
    total = {k: sum(t[k] for t in toks) for k in ("input", "cached", "output", "reasoning")}
    unknown = missing = n_tool = 0
    for r in rows:
        catalog = _tool_catalog(r)
        for c in r.get("policy_calls") or []:
            offered = set(c.get("tools") or [])
            for tc in c.get("tool_calls") or []:
                n_tool += 1
                if tc["name"] not in offered:
                    unknown += 1
                elif set((catalog.get(tc["name"], {}).get("inputSchema") or {}).get("required") or []) - set(tc.get("arguments") or {}):
                    missing += 1
    per_episode_last = [_tokens((r.get("policy_calls") or [{}])[-1].get("usage"))["input"] for r in rows if r.get("policy_calls")]
    out: dict[str, Any] = {
        "calls": len(calls),
        "calls_per_episode": len(calls) / max(1, len(rows)),
        "tokens_per_call": {k: v / len(calls) for k, v in total.items()},
        "tokens_per_episode": {k: v / max(1, len(rows)) for k, v in total.items()},
        "cache_hit_rate": total["cached"] / total["input"] if total["input"] else None,
        "context_last_turn_mean": statistics.fmean(per_episode_last) if per_episode_last else None,
        "gym_call_latency_ms": percentiles([c.get("latency_ms") for c in calls]),
        "error_rate": sum(bool(c.get("error")) for c in calls) / len(calls),
        "empty_response_rate": sum(not (c.get("text") or c.get("tool_calls")) and not c.get("error") for c in calls) / len(calls),
        "tool_calls_per_episode": n_tool / max(1, len(rows)),
        "tool_validity": {"tool_calls": n_tool, "unknown_tool_per_100": 100 * unknown / max(1, n_tool),
                          "missing_required_arg_per_100": 100 * missing / max(1, n_tool)},
        "served_models": dict(collections.Counter(c.get("served_model") for c in calls)),
    }
    if prices:  # USD per 1M tokens: input (uncached), cached input, output
        cost = ((total["input"] - total["cached"]) * prices["input"] + total["cached"] * prices["cached"]
                + total["output"] * prices["output"]) / 1e6
        words = sum(len((t.get("said") or t.get("text") or "").split()) for r in rows for t in r.get("transcript") or [])
        minutes = words / SPOKEN_WPM + sum(c.get("latency_ms") or 0 for c in calls) / 60000
        out["cost_usd"] = {"total": cost, "per_episode": cost / max(1, len(rows)),
                           "per_call_minute_estimated": cost / minutes if minutes else None}
    return out


def caller_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    calls = [c for r in rows for c in r.get("user_calls") or []]
    toks = [_tokens(c.get("usage")) for c in calls]
    return {"calls": len(calls), "served_models": dict(collections.Counter(c.get("served_model") for c in calls)),
            "latency_ms": percentiles([c.get("latency_ms") for c in calls]),
            "tokens": {k: sum(t[k] for t in toks) for k in ("input", "cached", "output", "reasoning")}}


def build(run_dir: Path, clean_dir: Path | None = None, prices: dict[str, float] | None = None) -> dict[str, Any]:
    rows = [json.loads(line) for line in (run_dir / "rollouts.jsonl").read_text().splitlines() if line.strip()]
    profile = next((r.get("asr_profile") for r in rows if r.get("asr_profile")), "")
    report: dict[str, Any] = {
        "run": run_dir.name, "asr_profile": profile or None,
        "task": task_metrics(rows), "speakability": speakability(rows),
        "llm": llm_metrics(rows, prices), "caller": caller_metrics(rows),
    }
    if profile:
        report["channel"] = channel_metrics(rows)
        targets = PROFILES / f"{profile}.stats.json"
        if targets.is_file():
            report["channel"]["targets"] = json.loads(targets.read_text())
    if clean_dir:
        clean = [json.loads(line) for line in (clean_dir / "rollouts.jsonl").read_text().splitlines() if line.strip()]
        report["robustness"] = {"clean_run": clean_dir.name, **robustness_drop(clean, rows)}
    report["latency"] = {p.name.removesuffix(".summary.json"): json.loads(p.read_text())
                         for p in sorted(run_dir.glob("latency-*.summary.json"))}
    (run_dir / "report.json").write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    # self-check on two synthetic rollouts: one clean pass, one misheard phone written to the DB
    said = "My number is two one four, five five five, zero one six three."
    ok = {"industry": "x", "case_key": "a", "conjunctive": 1.0, "components": {}, "final_state": {},
          "transcript": [{"role": "customer", "said": said, "heard_segments": ["My number is 214-555-0163."]},
                         {"role": "agent", "text": "Thanks."}]}
    bad = {"industry": "x", "case_key": "b", "conjunctive": 0.0, "components": {},
           "final_state": {"callers": [{"phone": "2145550136"}]},
           "transcript": [{"role": "customer", "said": said, "heard_segments": ["My number is 214-555-0136."]},
                          {"role": "agent", "text": "Got it, 214-555-0136. Could you confirm that?"}]}
    ch = channel_metrics([ok, bad])
    assert ch["misheard_write_rate"] == 1.0 and ch["readback_rate"] == 1.0 and ch["clarification_rate"] == 1.0, ch
    assert ch["pass_by_outcome"]["digits_broken"]["pass_rate"] == 0.0, ch
    tm = task_metrics([ok, bad, dict(ok, case_key="b")])
    assert tm["pass_at_k"] == 1.0 and tm["pass_hat_k"] == 0.5 and tm["k"] == 2, tm
    rd = robustness_drop([ok, dict(bad, conjunctive=1.0)], [ok, bad])
    assert rd["paired_tasks"] == 2 and rd["drop"] == 0.5, rd
    assert speakability([{"transcript": [{"role": "agent", "text": "**Sure**"}]}])["markdown_rate"] == 1.0
    print("report self-check ok")
