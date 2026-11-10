"""`micol` CLI: local episodes, the oracle, re-scoring, and NeMo Gym datasets.

  micol run     --industry healthcare --task hc-tgcr [--out episodes]
  micol oracle  --industry healthcare [--task hc-tgcr | --all]
  micol verify  episodes/hc-tgcr [--reward-dir DIR]
  micol dataset --industry healthcare [--out resources_servers/micol/data/healthcare.jsonl]
  micol ui      [--port 8765]   web console over runs, tasks, and rollouts

`run` needs no NeMo Gym. Models are OpenAI-compatible chat endpoints, wired per role:
  MICOL_AGENT_MODEL / MICOL_AGENT_BASE_URL / MICOL_AGENT_API_KEY   model under test
  MICOL_USER_MODEL  / MICOL_USER_BASE_URL  / MICOL_USER_API_KEY    caller simulator
Unset role vars fall back to OPENAI_BASE_URL / OPENAI_API_KEY; both models default to gpt-5.2.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import bench, verify
from .env import Session, ToolServers, oracle_replay
from .llm import OpenAIChat
from .loop import ChatPolicy, LocalEnv, run_episode
from .usersim import temperature


def _llm(role: str, *, temp: float | None = None) -> OpenAIChat:
    return OpenAIChat(
        os.environ.get(f"MICOL_{role}_MODEL", "gpt-5.2"),
        base_url=os.environ.get(f"MICOL_{role}_BASE_URL") or None,
        api_key=os.environ.get(f"MICOL_{role}_API_KEY") or None,
        temperature=temp,
    )


def _keys(args) -> list[str]:
    if args.all:
        return bench.list_tasks(args.industry)
    if not args.task:
        raise SystemExit("pass --task CASE_KEY or --all")
    return [args.task]


def _write(out_dir: Path, case_key: str, result: dict[str, Any], scored: dict[str, Any], messages: list[dict[str, Any]] | None = None) -> None:
    case_dir = out_dir / case_key
    case_dir.mkdir(parents=True, exist_ok=True)
    episode = dict(result)
    if messages is not None:
        episode["messages"] = messages
    (case_dir / "episode.json").write_text(json.dumps(episode, indent=2))
    (case_dir / "result.json").write_text(json.dumps(scored, indent=2))
    (case_dir / "reward.json").write_text(json.dumps(verify.reward_file(scored)))


def _summary_line(label: str, case_key: str, scored: dict[str, Any]) -> str:
    comp = scored["components"]
    mark = "PASS" if scored["passed"] else "FAIL"
    return (f"{label}{mark} {case_key}  tools={comp['tool_adherence']['passed']} "
            f"handoffs={comp['handoff_adherence']['passed']} "
            f"state={comp['state_adherence']['passed']}  shaped={scored['shaped']:.3f}")


def cmd_run(args) -> int:
    servers = ToolServers()
    out_dir = Path(args.out)
    passed = 0
    keys = _keys(args)
    try:
        for key in keys:
            task = bench.load_task(args.industry, key)
            session = Session(args.industry, key, servers.for_task(args.industry, key),
                              _llm("USER", temp=temperature(task)))
            try:
                messages = asyncio.run(run_episode(ChatPolicy(_llm("AGENT")), LocalEnv(session)))
                result, scored = session.score()
            finally:
                session.close()
            _write(out_dir, key, result, scored, messages)
            print(_summary_line("", key, scored))
            passed += scored["passed"]
    finally:
        servers.stop_all()
    print(f"\n{passed}/{len(keys)} passed")
    return 0 if passed == len(keys) else 1


def cmd_oracle(args) -> int:
    """Replay the answer key with no LLM; every well-formed task scores 1.0."""
    servers = ToolServers()
    failed = []
    keys = _keys(args)
    try:
        for key in keys:
            session = Session(args.industry, key, servers.for_task(args.industry, key))
            try:
                oracle_replay(session)
                result, scored = session.score()
            finally:
                session.close()
            if args.out:
                _write(Path(args.out), key, result, scored)
            if not scored["passed"]:
                failed.append(key)
                print(_summary_line("ORACLE ", key, scored))
    finally:
        servers.stop_all()
    print(f"oracle: {len(keys) - len(failed)}/{len(keys)} tasks replay to conjunctive 1.0")
    if failed:
        print("answer key and expected state disagree on: " + ", ".join(failed), file=sys.stderr)
    return 0 if not failed else 1


def cmd_verify(args) -> int:
    """Re-score a saved episode. Exit 0 whenever scoring ran; reward.json carries the verdict."""
    episode_dir = Path(args.episode_dir)
    episode = json.loads((episode_dir / "episode.json").read_text())
    task = bench.load_task(episode["industry"], episode["task"])
    scored = verify.score(episode["industry"], task, episode)
    (episode_dir / "result.json").write_text(json.dumps(scored, indent=2))
    reward_dir = Path(args.reward_dir) if args.reward_dir else episode_dir
    reward_dir.mkdir(parents=True, exist_ok=True)
    (reward_dir / "reward.json").write_text(json.dumps(verify.reward_file(scored)))
    print(_summary_line("", episode["task"], scored))
    return 0


def cmd_freeze(args) -> int:
    """Write exp_db_state for a new task by replaying its answer key; non-zero if the key is broken."""
    from micol.env import freeze
    servers = ToolServers()
    try:
        problems = freeze(args.industry, args.task, servers)
    finally:
        servers.stop_all()
    for p in problems:
        print(f"PROBLEM {p}")
    print("frozen" if not problems else f"{len(problems)} problem(s); exp_db_state not written")
    return 1 if problems else 0


def cmd_dataset(args) -> int:
    """NeMo Gym JSONL: one row per text case, identifiers only. Prompts, tools,
    and the caller brief are served by the environment, never copied into rows."""
    def meta(k: str) -> dict:
        return bench.load_task(args.industry, k).get("metadata") or {}
    keys = [k for k in bench.list_tasks(args.industry)
            if meta(k).get("split") == ("private" if args.private else "public")
            and (not args.tag or args.tag in (meta(k).get("tags") or []))]
    if args.limit:
        keys = keys[: args.limit]
    name = f"{args.industry}-private" if args.private else args.industry
    if args.tag:
        name += f"-{args.tag.replace(':', '-')}"
    out = Path(args.out or f"resources_servers/micol/data/{name}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for key in keys:
            meta = bench.load_task(args.industry, key).get("metadata") or {}
            row = {
                "industry": args.industry,
                "case_key": key,
                "category": meta.get("category"),
                "difficulty": meta.get("difficulty"),
                "responses_create_params": {"input": []},
            }
            f.write(json.dumps(row) + "\n")
    print(f"{len(keys)} rows -> {out}")
    return 0


def cmd_latency(args) -> int:
    """Replay a run's policy requests streamed, one at a time, and time them."""
    from openai import OpenAI

    from . import latency
    from .latency import run

    latency.OPENING, latency.API = args.opening, args.api
    client = OpenAI(base_url=args.base_url or None, api_key=os.environ.get(args.api_key_env))
    extra = json.loads(args.extra) if args.extra else None
    summary = run(Path(__file__).resolve().parents[2] / "runs" / args.run, client, args.model, warmup=args.warmup, limit=args.limit, extra=extra)
    print(json.dumps(summary, indent=1))
    return 0


def cmd_report(args) -> int:
    """Phone-LLM bench report for a run: task, channel, LLM call and latency metrics."""
    from .report import build

    runs = Path(__file__).resolve().parents[2] / "runs"
    prices = dict(zip(("input", "cached", "output"), map(float, args.price.split(",")))) if args.price else None
    report = build(runs / args.run, runs / args.clean if args.clean else None, prices)
    print(json.dumps(report, indent=1))
    return 0


def cmd_ui(args) -> int:
    import uvicorn

    print(f"MICOL console on http://{args.host}:{args.port}")
    uvicorn.run("micol.console.api:app", host=args.host, port=args.port, log_level="warning")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="micol")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="play text episodes locally (no NeMo Gym)")
    orc_p = sub.add_parser("oracle", help="replay the answer key, no LLM")
    for p in (run_p, orc_p):
        p.add_argument("--industry", required=True)
        p.add_argument("--task", help="task_id, e.g. hc-tgcr")
        p.add_argument("--all", action="store_true")
    run_p.add_argument("--out", default="episodes")
    orc_p.add_argument("--out", help="also write episode artifacts here")
    run_p.set_defaults(fn=cmd_run)
    orc_p.set_defaults(fn=cmd_oracle)

    ver_p = sub.add_parser("verify", help="re-score a saved episode")
    ver_p.add_argument("episode_dir")
    ver_p.add_argument("--reward-dir")
    ver_p.set_defaults(fn=cmd_verify)

    fr_p = sub.add_parser("freeze", help="replay a new task's answer key and write its exp_db_state")
    fr_p.add_argument("--industry", required=True)
    fr_p.add_argument("--task", required=True)
    fr_p.set_defaults(fn=cmd_freeze)

    ds_p = sub.add_parser("dataset", help="write NeMo Gym JSONL rows for an industry")
    ds_p.add_argument("--industry", required=True)
    ds_p.add_argument("--out")
    ds_p.add_argument("--limit", type=int)
    ds_p.add_argument("--private", action="store_true", help="the private tasks instead of the public set")
    ds_p.add_argument("--tag", help="only tasks carrying this metadata tag, e.g. mivas-v1")
    ds_p.set_defaults(fn=cmd_dataset)

    lat_p = sub.add_parser("latency", help="replay a run's policy requests streamed; TTFT, TTFS, TPOT, speed")
    lat_p.add_argument("--run", required=True, help="run id under runs/")
    lat_p.add_argument("--model", required=True)
    lat_p.add_argument("--base-url", help="OpenAI-compatible endpoint; default OpenAI")
    lat_p.add_argument("--api-key-env", default="OPENAI_API_KEY")
    lat_p.add_argument("--warmup", type=int, default=2)
    lat_p.add_argument("--limit", type=int, help="time at most this many calls")
    lat_p.add_argument("--api", choices=["chat_completions", "responses"], default="chat_completions")
    lat_p.add_argument("--opening", help="user turn to append to system-only requests (the config's opening_user_message)")
    lat_p.add_argument("--extra", help="JSON of extra request fields, e.g. '{\"reasoning_effort\": \"none\"}'")
    lat_p.set_defaults(fn=cmd_latency)

    rep_p = sub.add_parser("report", help="phone-LLM bench report for a run; writes runs/<id>/report.json")
    rep_p.add_argument("--run", required=True)
    rep_p.add_argument("--clean", help="clean-caller run of the same tasks, for the paired robustness drop")
    rep_p.add_argument("--price", help="USD per 1M tokens: input,cached,output (e.g. 2,0.5,8)")
    rep_p.set_defaults(fn=cmd_report)

    ui_p = sub.add_parser("ui", help="web console: trigger runs, inspect rollouts and grading")
    ui_p.add_argument("--host", default="127.0.0.1")
    ui_p.add_argument("--port", type=int, default=8765)
    ui_p.set_defaults(fn=cmd_ui)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
