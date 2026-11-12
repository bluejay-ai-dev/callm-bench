"""What the console shows for one rollout: the call as a timeline, and the grade broken down."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from callm import bench, grader


def attempt(r: dict[str, Any]) -> int:
    return int(r.get("_ng_rollout_index") or 0)


def task_key(r: dict[str, Any]) -> tuple[str, str]:
    return (r["industry"], r["case_key"])


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pass counts per industry and overall.

    Rollout-level counts (n, passed, tools, ...) count every attempt; task-level counts group a
    task's k attempts: pass_any (pass@k, at least one attempt passed) and pass_all (pass^k).
    """
    def block(rs: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rs)
        ok = lambda part: sum(bool(r["components"][part]["passed"]) for r in rs if r.get("components"))
        by_task: dict[tuple[str, str], list[bool]] = {}
        for r in rs:
            by_task.setdefault(task_key(r), []).append(bool(r.get("conjunctive")))
        return {
            "n": n,
            "passed": sum(1 for r in rs if r.get("conjunctive")),
            "tools": ok("tool_adherence"),
            "handoffs": ok("handoff_adherence"),
            "db": ok("state_adherence"),
            "shaped": round(sum(r.get("shaped") or 0 for r in rs) / n, 4) if n else None,
            "errors": sum(1 for r in rs if r.get("failure_kind")),
            "tasks": len(by_task),
            "k": max((len(v) for v in by_task.values()), default=0),
            "pass_any": sum(1 for v in by_task.values() if any(v)),
            "pass_all": sum(1 for v in by_task.values() if all(v)),
        }
    industries = sorted({r["industry"] for r in rows})
    return {"all": block(rows), "by_industry": {i: block([r for r in rows if r["industry"] == i]) for i in industries}}


@lru_cache(maxsize=None)
def _tag_title(industry: str, case_key: str) -> tuple[str, str]:
    try:
        t = bench.load_task(industry, case_key)
    except SystemExit:
        return "?", case_key
    return bench.task_tag(t), t.get("task_name") or case_key


def row_brief(r: dict[str, Any]) -> dict[str, Any]:
    c = r.get("components") or {}
    tag, title = _tag_title(r["industry"], r["case_key"])
    return {
        "industry": r["industry"], "case_key": r["case_key"], "attempt": attempt(r),
        "tag": tag, "title": title,
        "category": r.get("category"), "difficulty": r.get("difficulty"),
        "passed": bool(r.get("conjunctive")), "shaped": r.get("shaped"),
        "tools": bool(c.get("tool_adherence", {}).get("passed")),
        "handoffs": bool(c.get("handoff_adherence", {}).get("passed")),
        "db": bool(c.get("state_adherence", {}).get("passed")),
        "ended_by": r.get("ended_by"), "failure_kind": r.get("failure_kind"),
        "turns": len(r.get("transcript") or []), "tool_calls": len(r.get("trace") or []),
    }


def attempts_of(rows: list[dict[str, Any]], industry: str, case_key: str) -> list[dict[str, Any]]:
    """One task's attempts in a run, in attempt order."""
    return sorted((r for r in rows if task_key(r) == (industry, case_key)), key=attempt)


def _json(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    try:
        return json.loads(text)
    except ValueError:
        return text


def _message_text(item: dict[str, Any]) -> str:
    content = item.get("content")
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or [] if isinstance(part, dict))


def timeline(r: dict[str, Any]) -> list[dict[str, Any]]:
    """Messages and tool calls in call order, with a marker wherever the active agent changed.

    Sources, best first: transcript turns stamped on the tool clock (current runs), the
    Responses trajectory Gym records (older Gym runs), or tool calls alone (oracle).
    """
    trace = r.get("trace") or []
    transcript = r.get("transcript") or []
    events: list[dict[str, Any]] = []
    if transcript and all("offset_ms" in t for t in transcript):
        merged = [(t["offset_ms"], 1, {"kind": "message", "role": t["role"], "text": t["text"],
                                       **({"said": t["said"]} if "said" in t else {}),
                                       **({"dropped": True} if t.get("dropped") else {})}) for t in transcript]
        merged += [(c.get("start_offset_ms", 0), 0, {"kind": "tool", "index": i}) for i, c in enumerate(trace)]
        events = [e for _, _, e in sorted(merged, key=lambda x: (x[0], x[1]))]
    elif (r.get("response") or {}).get("output") is not None:
        items = [i for i in (r.get("responses_create_params") or {}).get("input") or []
                 if i.get("role") != "system"] + r["response"]["output"]
        outputs = {i.get("call_id"): _json(i.get("output")) for i in items if i.get("type") == "function_call_output"}
        n = 0
        for item in items:
            if item.get("type") == "function_call":
                events.append({"kind": "tool", "index": n, "result": outputs.get(item.get("call_id"))})
                n += 1
            elif item.get("type", "message") == "message" and item.get("role") in ("assistant", "user"):
                text = _message_text(item)
                if text:
                    events.append({"kind": "message", "role": "agent" if item["role"] == "assistant" else "customer",
                                   "text": text})
    else:
        events = [{"kind": "tool", "index": i} for i in range(len(trace))]

    swaps = {s["after_tool_call"]: s["agent"] for s in (r.get("system_prompt_swaps") or [])[1:]}
    out: list[dict[str, Any]] = []
    seen = 0
    for e in events:
        if e["kind"] == "tool":
            call = trace[e["index"]] if e["index"] < len(trace) else {}
            out.append({**e, "name": call.get("name"), "parameters": call.get("parameters"),
                        "agent": call.get("agent"), "ok": call.get("ok"), "error_code": call.get("error_code"),
                        "result": e.get("result", call.get("result"))})
            seen += 1
            if seen in swaps:
                out.append({"kind": "handoff", "agent": swaps[seen]})
        else:
            out.append(e)
    return out


def _compare_args(industry: str, exp: dict[str, Any], act: dict[str, Any], tool: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Each argument the answer key constrains, judged the way grader._calls_match judges it,
    then the arguments the agent added that the grader does not look at."""
    exp_params = {k: v for k, v in grader._params_of(exp).items() if grader._present_nonempty(v)}
    act_params = grader._industry_params(grader._params_of(act), tool)
    rows = []
    for key, want in exp_params.items():
        got = act_params.get(key)
        if industry == "legal" and key == "reason":
            status = "ignored"
        elif grader._is_prose_arg(key, grader._prop_schema(tool, key), industry):
            status = "prose" if key not in act_params or grader._present_nonempty(got) else "empty"
        elif key not in act_params:
            default = grader._omitted_default(str(exp.get("name") or ""), key, act_params)
            status = "default" if default is not grader._NO_DEFAULT and grader._values_equal(key, want, default) else "missing"
        else:
            status = "match" if grader._values_equal(key, want, got) else "differs"
        rows.append({"key": key, "expected": want, "actual": got, "present": key in act_params, "status": status})
    for key, got in act_params.items():
        if key not in exp_params:
            rows.append({"key": key, "expected": None, "actual": got, "present": True, "status": "unchecked"})
    return rows


def _outcome(exp: dict[str, Any] | None, act: dict[str, Any] | None) -> dict[str, Any]:
    want = grader._output_fields(exp) if exp else {}
    got = grader._output_fields(act) if act else {}
    ok = all(want[f] == got[f] for f in ("ok", "error_code") if f in want and f in got)
    return {"expected": want or None, "actual": got or None, "match": ok}


def grading(industry: str, task: dict[str, Any], r: dict[str, Any]) -> dict[str, Any]:
    """The grade broken down for display.

    Tool rows follow the agent's call order, then expected calls it never made. Pairing first
    reproduces the grader's own greedy pass (each expected call takes the first unused actual
    call that satisfies it), so "match" agrees with the score; an expected call left unmatched
    is then paired with the next unused call of the same tool, so a near miss shows what differed
    instead of reading as one missing call and one unrelated extra.
    """
    trace = r.get("trace") or []
    schemas = grader.load_tool_schemas(industry)
    exp_calls: list[dict[str, Any]] = task.get("exp_tool_calls") or []
    pair: dict[int, int] = {}  # actual index -> expected index
    for ei, exp in enumerate(exp_calls):
        ai = next((i for i, act in enumerate(trace)
                   if i not in pair and grader._calls_match(exp, act, schemas, industry)), None)
        if ai is not None:
            pair[ai] = ei
    graded = set(pair)
    def misses(exp: dict[str, Any], act: dict[str, Any]) -> int:
        args = _compare_args(industry, exp, act, schemas.get(act.get("name") or ""))
        return sum(a["status"] in ("differs", "missing", "empty") for a in args) + (not _outcome(exp, act)["match"])

    for ei, want in enumerate(exp_calls):
        if ei not in pair.values():
            same = [i for i, act in enumerate(trace) if i not in pair and act.get("name") == want.get("name")]
            if same:
                pair[min(same, key=lambda i: (misses(want, trace[i]), i))] = ei  # the closest attempt

    comp = r.get("components") or {}
    forbidden = set(comp.get("tool_adherence", {}).get("extra") or [])
    rows = []
    for ai, act in enumerate(trace):
        ei = pair.get(ai)
        exp = exp_calls[ei] if ei is not None else None
        args = _compare_args(industry, exp, act, schemas.get(act.get("name") or "")) if exp else [
            {"key": k, "expected": None, "actual": v, "present": True, "status": "unchecked"}
            for k, v in (act.get("parameters") or {}).items()]
        outcome = _outcome(exp, act)
        if exp is None:
            status = "forbidden" if act.get("name") in forbidden else "extra"
        elif ai in graded:
            status = "match"
        else:
            bad_args = any(a["status"] in ("differs", "missing", "empty") for a in args)
            status = "params_and_output_differ" if bad_args and not outcome["match"] else (
                "params_differ" if bad_args else "output_differs" if not outcome["match"] else "params_differ")
        rows.append({"status": status, "name": act.get("name"), "actual_index": ai, "expected_index": ei,
                     "agent": act.get("agent"), "args": args, "outcome": outcome, "reply": act.get("result")})
    for ei, exp in enumerate(exp_calls):
        if ei not in pair.values():
            rows.append({"status": "missing", "name": exp.get("name"), "actual_index": None, "expected_index": ei,
                         "agent": None, "args": [{"key": k, "expected": v, "actual": None, "present": False,
                                                  "status": "missing"} for k, v in grader._params_of(exp).items()],
                         "outcome": _outcome(exp, None), "reply": None})

    names = [c.get("name") for c in trace]
    exp_db = grader.office_canonical(task.get("exp_db_state"), industry) if task.get("exp_db_state") else {}
    act_db = grader.office_canonical(r.get("final_state") or {}, industry)
    tables = [{"table": t, "expected": exp_db.get(t), "actual": act_db.get(t), "same": exp_db.get(t) == act_db.get(t)}
              for t in exp_db]
    return {
        "tool_rows": rows,
        "expected_count": len(exp_calls),
        "actual_count": len(trace),
        "handoffs": {"expected": grader.expected_handoff_path(task), "actual": grader.actual_handoffs(names, industry)},
        "db_tables": tables,
        "components": comp,
        "scores": {k: r.get(k) for k in ("conjunctive", "shaped", "tool_reward", "handoff_reward", "state_reward")},
    }
