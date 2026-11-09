"""Latency pass: replay a run's recorded policy requests against a provider, streamed, one at a time.

Accuracy runs go through Gym's non-streaming model servers, so token timings come from here:
each `policy_calls[].request` in `runs/<id>/rollouts.jsonl` is re-sent with `stream=True` and
timed client side. Run it from a quiet host; warm-up calls are dropped.
"""

from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from . import bench
from .llm import tool_decl

SENTENCE_END = re.compile(r"[.!?](\s|$)")
MESSAGE_KEYS = ("role", "content", "tool_calls", "tool_call_id", "name")


def requests_from_run(run_dir: Path) -> list[dict[str, Any]]:
    """Rebuild each policy request: the active swap's system prompt + the episode history up to
    that call + the offered tools, declared from the industry's tools.json."""
    out = []
    for line in (run_dir / "rollouts.jsonl").read_text().splitlines():
        row = json.loads(line)
        swaps, history = row.get("system_prompt_swaps") or [], row.get("policy_history") or []
        if not (swaps and history):
            continue
        task = bench.load_task(row["industry"], row["case_key"])
        catalog = {t["name"]: t for t in json.loads(
            bench.pack_file(row["industry"], "tools.json", bench.task_variant(task)).read_text())["tools"]}
        for call in row.get("policy_calls") or []:
            if call.get("swap") is None:
                continue
            system = {"role": "system", "content": swaps[call["swap"]]["system_prompt"]}
            out.append({"case_key": row["case_key"], "i": call["i"],
                        "messages": [system, *history[: call["n_history"]]],
                        "tools": [tool_decl(catalog[n]) for n in call.get("tools") or [] if n in catalog]})
    return out


# The user turn chat_passthrough appends to a system-only request (configs' opening_user_message).
OPENING: str | None = None


def _clean(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = [{k: m[k] for k in MESSAGE_KEYS if m.get(k) is not None} for m in messages]
    if OPENING and all(m["role"] in ("system", "developer") for m in out):
        out.append({"role": "user", "content": OPENING})
    return out


def time_call(client: Any, model: str, req: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    t0 = time.perf_counter()
    first = first_text = first_sentence = None
    text, out_tokens = "", None
    stream = client.chat.completions.create(
        model=model, messages=_clean(req["messages"]), tools=req.get("tools") or None,
        stream=True, stream_options={"include_usage": True}, extra_body=extra or None)
    for chunk in stream:
        now = time.perf_counter() - t0
        if chunk.usage:
            out_tokens = chunk.usage.completion_tokens
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if first is None and (delta.content or delta.tool_calls):
            first = now
        if delta.content:
            text += delta.content
            if first_text is None:
                first_text = now
            if first_sentence is None and SENTENCE_END.search(text):
                first_sentence = now
    end = time.perf_counter() - t0
    if first_sentence is None and text.strip():
        first_sentence = end  # a reply with no sentence break is one sentence
    decode = (end - first) if first is not None else None
    return {
        "case_key": req["case_key"], "i": req["i"],
        "ttft_ms": _ms(first), "ttf_text_ms": _ms(first_text), "ttfs_ms": _ms(first_sentence), "e2e_ms": _ms(end),
        "output_tokens": out_tokens,
        "tpot_ms": _ms(decode / (out_tokens - 1)) if decode and out_tokens and out_tokens > 1 else None,
        "tokens_per_s": round(out_tokens / decode, 1) if decode and out_tokens else None,
    }


def _ms(seconds: float | None) -> float | None:
    return None if seconds is None else round(seconds * 1000, 1)


def percentiles(values: list[float]) -> dict[str, float] | None:
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    q = statistics.quantiles(values, n=100, method="inclusive") if len(values) > 1 else [values[0]] * 99
    return {"n": len(values), "p50": round(q[49], 1), "p90": round(q[89], 1),
            "p95": round(q[94], 1), "p99": round(q[98], 1)}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in rows if not r.get("error")]
    out: dict[str, Any] = {k: percentiles([r[k] for r in ok]) for k in ("ttft_ms", "ttf_text_ms", "ttfs_ms", "e2e_ms")}
    tpot = [r["tpot_ms"] for r in ok if r["tpot_ms"] is not None]
    speed = [r["tokens_per_s"] for r in ok if r["tokens_per_s"] is not None]
    out["tpot_ms_mean"] = round(statistics.fmean(tpot), 2) if tpot else None
    out["tpot_ms_p95"] = (percentiles(tpot) or {}).get("p95")
    out["tokens_per_s_median"] = statistics.median(speed) if speed else None
    out["calls"], out["errors"] = len(rows), len(rows) - len(ok)
    return out


def run(run_dir: Path, client: Any, model: str, *, warmup: int = 2, limit: int | None = None,
        extra: dict[str, Any] | None = None) -> dict[str, Any]:
    reqs = requests_from_run(run_dir)
    if limit:
        reqs = reqs[:: max(1, len(reqs) // (limit + warmup))][: limit + warmup]  # spread over every task
    rows = []
    for n, req in enumerate(reqs):
        try:
            row = time_call(client, model, req, extra or {})
        except Exception as error:  # noqa: BLE001 -- one failed call is a reliability data point
            row = {"case_key": req["case_key"], "i": req["i"], "error": f"{type(error).__name__}: {error}"[:300]}
        if n >= warmup:
            rows.append(row)
    out_path = run_dir / f"latency-{model.replace('/', '_')}.jsonl"
    out_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    summary = {"model": model, "run": run_dir.name, **summarize(rows)}
    (run_dir / f"latency-{model.replace('/', '_')}.summary.json").write_text(json.dumps(summary, indent=1))
    return summary


if __name__ == "__main__":
    # self-check: percentiles and summary on fixed rows
    rows = [{"ttft_ms": v, "ttf_text_ms": v, "ttfs_ms": v + 10, "e2e_ms": v + 50, "output_tokens": 11,
             "tpot_ms": 5.0, "tokens_per_s": 200.0} for v in range(100, 200)]
    s = summarize(rows + [{"error": "x"}])
    assert s["ttft_ms"]["p50"] == 149.5 and s["ttfs_ms"]["p95"] == 204.1 and s["errors"] == 1, s
    assert SENTENCE_END.search("Sure. Let me") and not SENTENCE_END.search("v1.2 is")
    print("ok")
