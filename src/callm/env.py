"""The CALLM environment: industry tool server, multi-agent DAG state, caller.

One ToolServer process serves many episodes — the pack's runtime scopes state
per call via the X-Callm-Call-Id header (fresh seeded SQLite per call id), so
each Session just mints a new call id.

Tool execution mirrors the voice harnesses' contract exactly:
- handoff tools (blueprint `handoff: true`) switch the active agent: the next
  model call gets that agent's system prompt and toolset, history unchanged
- `end_call` ends the episode
- other session tools POST /tools/{name}, then end the episode
- industry tools POST /tools/{name}
- a tool the active agent does not own is refused (UNKNOWN_TOOL)
Every call lands in `trace` in wall-clock order, the shape
grader.tool_call_adherence consumes.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from . import bench, grader, verify
from .db_service import unlink_db
from .llm import tool_decl
from .usersim import SPLIT, UserSim, load_profile, load_rates


class ToolServer:
    """The industry pack's FastAPI + SQLite tool server, as a local subprocess."""

    def __init__(self, industry: str, port: int | None = None, variant: str | None = None):
        self.industry = industry
        self.variant = variant
        self.industry_dir = bench.industry_dir(industry)
        self.port = port or _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc: subprocess.Popen[bytes] | None = None
        self.data_dir: tempfile.TemporaryDirectory[str] | None = None

    def call_db(self, call_id: str) -> Path:
        """The per-call SQLite file db_service creates on a call's first request."""
        assert self.data_dir is not None, "tool server not started"
        return Path(self.data_dir.name) / "calls" / f"{call_id}.db"

    def start(self, timeout: float = 30.0) -> None:
        self.data_dir = tempfile.TemporaryDirectory(prefix=f"callm-{self.industry}-")
        env = dict(os.environ)
        env["TOOL_SERVER_PORT"] = str(self.port)
        env["CALLM_DB_PATH"] = str(Path(self.data_dir.name) / "industry.db")
        overlay = bench.variant_dir(self.industry, self.variant)
        if overlay is not None:
            env["CALLM_VARIANT_DIR"] = str(overlay)
        self.proc = subprocess.Popen(
            [sys.executable, "tool_server.py"],
            cwd=self.industry_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{self.base}/health", timeout=1.0).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            if self.proc.poll() is not None:
                raise RuntimeError(f"{self.industry} tool server exited {self.proc.returncode}")
            time.sleep(0.2)
        self.stop()
        raise RuntimeError(f"{self.industry} tool server never became healthy")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.data_dir:
            self.data_dir.cleanup()
            self.data_dir = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()


class ToolServers:
    """Lazily started tool servers, one per (industry, variant), shared across sessions."""

    def __init__(self):
        self._servers: dict[tuple[str, str | None], ToolServer] = {}
        self._lock = threading.Lock()

    def get(self, industry: str, variant: str | None = None) -> ToolServer:
        with self._lock:
            server = self._servers.get((industry, variant))
            if server is None:
                server = ToolServer(industry, variant=variant)
                server.start()
                self._servers[(industry, variant)] = server
            return server

    def for_task(self, industry: str, case_key: str) -> ToolServer:
        return self.get(industry, bench.task_variant(bench.load_task(industry, case_key)))

    def stop_all(self) -> None:
        with self._lock:
            for server in self._servers.values():
                server.stop()
            self._servers.clear()


class Episode:
    """Tool execution + multi-agent DAG state for one call."""

    def __init__(self, blueprint: dict[str, Any], server: ToolServer, call_id: str | None = None):
        self.bp = blueprint
        self.server = server
        self.call_id = call_id or f"callm-{uuid.uuid4().hex[:16]}"
        self.agent = blueprint["start"]
        self.trace: list[dict[str, Any]] = []
        self.done = False
        self._t0 = time.monotonic()
        self._client = httpx.Client(timeout=30.0)

    def _tool_entry(self, name: str) -> dict[str, Any] | None:
        for t in self.bp["agents"][self.agent]["tools"]:
            if t["name"] == name:
                return t
        return None

    def active_tools(self) -> list[dict[str, Any]]:
        """Catalog specs for the active agent, in blueprint order."""
        return [
            self.bp["catalog"][t["name"]]
            for t in self.bp["agents"][self.agent]["tools"]
            if t["name"] in self.bp["catalog"]
        ]

    def active_instructions(self) -> str:
        return self.bp["agents"][self.agent]["instructions"]

    def offset_ms(self) -> int:
        """Milliseconds since the call started; orders transcript turns against tool calls."""
        return int((time.monotonic() - self._t0) * 1000)

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Run one tool call; records the trace entry; may set self.done."""
        offset_ms = self.offset_ms()
        entry: dict[str, Any] = {
            "name": name,
            "parameters": dict(args or {}),
            "start_offset_ms": offset_ms,
            "agent": self.agent,
        }
        spec = self._tool_entry(name)
        if spec is None:
            result: dict[str, Any] = {
                "ok": False,
                "error_code": "UNKNOWN_TOOL",
                "caller_safe_message": f"unknown tool {name!r} for agent {self.agent!r}",
            }
        elif spec.get("handoff"):
            target = spec.get("handoff_to")
            if target in self.bp["agents"]:
                self.agent = target
                result = {"success": True, "role": target}
            else:
                result = {"ok": False, "error_code": "BAD_HANDOFF"}
        elif name == "end_call":
            self.done = True
            result = {"success": True}
        else:
            resp = self._client.post(
                f"{self.server.base}/tools/{name}",
                json={"arguments": dict(args or {})},
                headers={"X-Callm-Call-Id": self.call_id},
            )
            result = resp.json()
            if spec.get("session"):
                self.done = True
        entry["ok"] = bool(result.get("ok") or result.get("success"))
        if result.get("error_code"):
            entry["error_code"] = result["error_code"]
        entry["result"] = result
        self.trace.append(entry)
        return result

    def final_state(self) -> dict[str, Any]:
        # After close the file is gone and /state would silently reseed a fresh DB.
        if self._client.is_closed:
            raise RuntimeError("episode closed; read final_state before close()")
        resp = self._client.get(f"{self.server.base}/state", params={"call_id": self.call_id})
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()
        unlink_db(self.server.call_db(self.call_id))


MAX_DROPPED_TURNS = 3  # consecutive recognizer drops before the caller's words are forced through


class Session:
    """One CALLM episode seen from the environment: what the model under test
    may see and do (active prompt, toolset), the caller it talks to, and every
    observable fact the verifier scores (trace, swaps, transcript, final DB).
    """

    def __init__(
        self,
        industry: str,
        case_key: str,
        server: ToolServer,
        user_llm: Any = None,
        *,
        call_id: str | None = None,
        asr_profile: str = "",
        asr_draws: bool = True,
        attempt: int = 0,
        channel_seed: int = 0,
    ):
        self.industry = industry
        self.task = bench.load_task(industry, case_key)
        variant = bench.task_variant(self.task)
        if server.variant != variant:
            raise ValueError(f"{case_key} needs the {variant or 'stock'} tool server, got {server.variant or 'stock'}")
        self.episode = Episode(bench.load_blueprint(industry, variant), server, call_id)
        self.asr_profile = asr_profile
        self.attempt = attempt
        # Draws are keyed by run seed, task and attempt, so every model under test meets the
        # same recognizer results on the same task attempt.
        rates = load_rates(asr_profile) if asr_profile and asr_draws else None
        self.user = UserSim(user_llm, self.task, load_profile(asr_profile), rates=rates,
                            draw_key=f"{channel_seed}|{industry}|{case_key}|{attempt}") if user_llm is not None else None
        self._pending: list[str] = []  # HEARD segments not yet delivered to the agent
        self._unheard = ""             # agent speech the caller has not replied to yet
        self.clock = bench.clock_line(industry)
        self.transcript: list[dict[str, Any]] = []
        self.ended_by: str | None = None
        self.swaps: list[dict[str, Any]] = []
        self._record_swap()

    @property
    def done(self) -> bool:
        return self.episode.done or self.ended_by is not None

    def system_prompt(self) -> str:
        prompt = self.episode.active_instructions()
        return f"{prompt}\n\n{self.clock}" if self.clock else prompt

    def state(self) -> dict[str, Any]:
        """What the model under test gets on its next call: messages[0] + tools."""
        return {
            "agent": self.episode.agent,
            "system_prompt": self.system_prompt(),
            "tools": [tool_decl(s) for s in self.episode.active_tools()],
            "done": self.done,
        }

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        before = self.episode.agent
        result = self.episode.execute(name, args)
        if self.episode.agent != before:
            self._record_swap()
        if self.episode.done and self.ended_by is None:
            self.ended_by = "agent"
        return result

    def end_turn(self, agent_text: str) -> dict[str, Any]:
        """Close the agent's turn; the caller replies unless the call already ended."""
        if agent_text:
            self.transcript.append({"role": "agent", "text": agent_text, "offset_ms": self.episode.offset_ms()})
        if self.done:
            return {"text": "", "hangup": False, "done": True}
        if self.user is None:
            raise RuntimeError("session has no user simulator")
        # A streaming cut delivers the rest of HEARD on the agent's next turns; the caller
        # hears what the agent said in between with its next reply.
        if self._pending:
            self._unheard = f"{self._unheard} {agent_text}".strip()
            piece = self._pending.pop(0)
            self.transcript.append({"role": "customer", "text": piece, "segment": True,
                                    "offset_ms": self.episode.offset_ms()})
            return {"text": piece, "hangup": False, "done": False}
        heard_by_caller = f"{self._unheard} {agent_text}".strip()
        self._unheard = ""
        # The agent never gets an empty turn: speech the recognizer dropped never reaches it, so
        # the caller hears silence and speaks again until something comes through.
        for dropped_in_a_row in range(MAX_DROPPED_TURNS + 1):
            text, hangup = self.user.reply(heard_by_caller)
            pieces = [p.strip() for p in text.split(SPLIT)] if self.user.channel else [text]
            pieces = [p for p in pieces if p]
            if self.user.channel and not pieces and not hangup and dropped_in_a_row == MAX_DROPPED_TURNS:
                pieces = [self.user.last_said]  # ponytail: ~1e-6 at real drop rates; deliver SAID rather than stall
            if pieces or self.user.channel:
                entry: dict[str, Any] = {"role": "customer", "text": pieces[0] if pieces else "",
                                         "offset_ms": self.episode.offset_ms()}
                if self.user.channel:
                    entry["said"] = self.user.last_said
                    entry["heard_segments"] = pieces
                    if not pieces:
                        entry["dropped"] = True
                    if self.user.last_draw is not None:
                        entry["draw"] = self.user.last_draw
                self.transcript.append(entry)
            if pieces or hangup or not self.user.channel:
                break
            heard_by_caller = ""  # the caller's next reply follows silence
        if hangup:
            self.ended_by = "customer"
        else:
            self._pending = pieces[1:]
        return {"text": pieces[0] if pieces else "", "hangup": hangup, "done": hangup}

    def result(self) -> dict[str, Any]:
        return {
            "industry": self.industry,
            "task": self.task["_case_key"],
            "transcript": self.transcript,
            "trace": self.episode.trace,
            "system_prompt_swaps": self.swaps,
            "final_state": self.episode.final_state(),
            "ended_by": self.ended_by or "max_exchanges",
            "call_id": self.episode.call_id,
            "final_agent": self.episode.agent,
        }

    def score(self) -> tuple[dict[str, Any], dict[str, Any]]:
        result = self.result()
        return result, verify.score(self.industry, self.task, result)

    def close(self) -> None:
        self.episode.close()

    def _record_swap(self) -> None:
        self.swaps.append({
            "after_tool_call": len(self.episode.trace),
            "agent": self.episode.agent,
            "system_prompt": self.system_prompt(),
        })


def oracle_replay(session: Session) -> None:
    """Deterministic reference run: execute exp_tool_calls with no LLM.

    Non-handoff calls are order-free across agents while hops are ordered, so
    each call runs under the agent that owns its tool, taking the next expected
    hop only when the active agent lacks the tool. A well-formed task scores
    conjunctive 1.0.

    Arguments are `parameters` (what the grader checks) plus `oracle_parameters`
    (reference values for arguments the task leaves to the agent, never graded);
    an `{"any_of": [...]}` constraint sends its first option.
    """
    hop_names = set(grader.handoff_tools_for(session.industry))
    expected = session.task.get("exp_tool_calls") or []
    hops = [c for c in expected if c["name"] in hop_names]
    calls = [c for c in expected if c["name"] not in hop_names]
    for call in calls:
        while hops and call["name"] not in {t["name"] for t in session.episode.active_tools()}:
            hop = hops.pop(0)
            session.call_tool(hop["name"], _oracle_args(hop))
        session.call_tool(call["name"], _oracle_args(call))
    for hop in hops:
        session.call_tool(hop["name"], _oracle_args(hop))
    if session.ended_by is None:
        session.ended_by = "oracle"


def freeze(industry: str, case_key: str, servers: "ToolServers") -> list[str]:
    """Replay a new task's answer key on a fresh DB and write the end state as exp_db_state.

    Returns what is wrong with the key; empty means the task is frozen and replays to 1.0.
    A call is expected to succeed unless its `output` says it is refused.
    """
    path = bench.industry_dir(industry) / "tasks" / case_key / "task.json"
    task = bench.load_task(industry, case_key)
    expected = task.get("exp_tool_calls") or []
    hop_names = set(grader.handoff_tools_for(industry))
    problems = []
    hops = [c["name"] for c in expected if c["name"] in hop_names]
    if hops != list(task.get("exp_handoff_path") or []):
        problems.append(f"exp_handoff_path {task.get('exp_handoff_path')} != the transfers in exp_tool_calls {hops}")
    session = Session(industry, case_key, servers.for_task(industry, case_key))
    try:
        oracle_replay(session)
        trace = list(session.episode.trace)
        state = session.episode.final_state()
    finally:
        session.close()
    seen: dict[str, int] = {}
    for call in expected:
        n = seen[call["name"]] = seen.get(call["name"], 0) + 1
        runs = [e for e in trace if e["name"] == call["name"]]
        entry = runs[n - 1] if len(runs) >= n else None
        want_ok = (call.get("output") or {}).get("ok", True)
        if entry is None:
            problems.append(f"{call['name']} #{n} never ran (no agent on the path owns it)")
        elif entry["ok"] != bool(want_ok):
            problems.append(f"{call['name']} #{n} returned {json.dumps(entry['result'])[:240]}")
    if problems:
        return problems
    task.pop("_case_key", None)
    # wall-clock stamps differ every replay; stored keys leave them out
    task["exp_db_state"] = {t: [{k: v for k, v in row.items() if k != "created_at"} if isinstance(row, dict) else row
                                for row in rows] if isinstance(rows, list) else rows
                            for t, rows in state.items()}
    path.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
    check = Session(industry, case_key, servers.for_task(industry, case_key))
    try:
        oracle_replay(check)
        _, scored = check.score()
    finally:
        check.close()
    return [] if scored["passed"] else [f"frozen key replays to {scored['conjunctive']}, not 1.0"]


def _oracle_args(call: dict[str, Any]) -> dict[str, Any]:
    def pick(value: Any) -> Any:
        if isinstance(value, dict) and "any_of" in value:
            return pick(value["any_of"][0])
        if isinstance(value, dict):
            return {k: pick(v) for k, v in value.items()}
        if isinstance(value, list):
            return [pick(v) for v in value]
        return value

    merged = {**(call.get("parameters") or {}), **(call.get("oracle_parameters") or {})}
    return pick(merged)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
