"""Runs on disk, the Gym server stack, and the queue that executes runs one at a time.

runs/<id>/meta.json      what was asked for and where it stands
runs/<id>/input.jsonl    the dataset rows ({industry, case_key, ...})
runs/<id>/rollouts.jsonl one scored rollout per line (Gym's output file for gym runs)
runs/<id>/eval.log       `gym eval run` output (gym runs)
runs/.stack.log          `gym env start` output for the current stack
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from micol import bench, verify
from micol.env import Session, ToolServers, oracle_replay

REPO = bench.REPO_ROOT
RUNS = REPO / "runs"
CONFIGS = REPO / "configs"
BIN = Path(sys.executable).parent
READY_RE = re.compile(r"All (\d+) / (\d+) servers ready")
ATTEMPT = "_ng_rollout_index"  # Gym's per-task repeat index (0..k-1); oracle runs write it too
ACTIVE = ("queued", "starting", "running")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def subprocess_env() -> dict[str, str]:
    """Process env plus the repo's .env (gitignored), with the venv's gym/ray on PATH."""
    env = dict(os.environ)
    dotenv = REPO / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text().splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key and not key.startswith("#"):
                env.setdefault(key.strip(), value.strip().strip("'\""))
    env["PATH"] = f"{BIN}{os.pathsep}{env.get('PATH', '')}"
    env["RAY_ENABLE_UV_RUN_RUNTIME_ENV"] = "0"  # Ray's uv hook breaks per-server venvs
    return env


def tail(path: Path, lines: int) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - lines * 400))
        text = f.read().decode(errors="replace")
    return "\n".join(re.split(r"[\r\n]+", text)[-lines:])


# ---------------------------------------------------------------- storage

_lock = threading.RLock()


def run_dir(run_id: str) -> Path:
    d = RUNS / run_id
    if not re.fullmatch(r"[\w.-]+", run_id) or not (d / "meta.json").is_file():
        raise KeyError(run_id)
    return d


def read_meta(run_id: str) -> dict[str, Any]:
    return json.loads((run_dir(run_id) / "meta.json").read_text())


def write_meta(meta: dict[str, Any]) -> None:
    with _lock:
        d = RUNS / meta["id"]
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / "meta.json.tmp"
        tmp.write_text(json.dumps(meta, indent=2))
        tmp.replace(d / "meta.json")


def update_meta(run_id: str, **fields: Any) -> dict[str, Any]:
    with _lock:
        meta = read_meta(run_id)
        meta.update(fields)
        write_meta(meta)
        return meta


def rollouts(run_id: str) -> list[dict[str, Any]]:
    path = run_dir(run_id) / "rollouts.jsonl"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # a line Gym is still writing
    return rows


def list_runs() -> list[dict[str, Any]]:
    if not RUNS.is_dir():
        return []
    metas = []
    for d in RUNS.iterdir():
        if (d / "meta.json").is_file():
            metas.append(json.loads((d / "meta.json").read_text()))
    return sorted(metas, key=lambda m: m["created_at"], reverse=True)


def create_run(kind: str, tasks: list[dict[str, str]], *, config: str | None, concurrency: int,
               label: str, repeats: int = 1, caller: str | None = None,
               source: dict[str, Any] | None = None) -> dict[str, Any]:
    """`caller` layers configs/users/<caller>.yaml over the config; `source` records who asked
    for the run (e.g. a factory run and step), shown with it."""
    if kind not in ("gym", "oracle"):
        raise ValueError(f"unknown run kind {kind!r}")
    if kind == "gym" and not (CONFIGS / f"{config}.yaml").is_file():
        raise ValueError(f"unknown config {config!r}")
    if caller and not (CONFIGS / "users" / f"{caller}.yaml").is_file():
        raise ValueError(f"unknown caller {caller!r}")
    if not tasks:
        raise ValueError("no tasks selected")
    rows = []
    for t in tasks:
        task = bench.load_task(t["industry"], t["case_key"])  # validates the pair
        meta = task.get("metadata") or {}
        rows.append({"industry": t["industry"], "case_key": t["case_key"],
                     "category": meta.get("category"), "difficulty": meta.get("difficulty"),
                     "responses_create_params": {"input": []}})
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{stamp}-{kind if kind == 'oracle' else config}-{uuid.uuid4().hex[:4]}"
    meta = {
        "id": run_id, "label": label or "", "kind": kind, "config": config if kind == "gym" else None,
        "caller": caller if kind == "gym" else None, "source": source or None,
        "concurrency": concurrency, "repeats": repeats, "total": len(rows) * repeats,
        "status": "queued", "error": None,
        "created_at": now(), "started_at": None, "finished_at": None,
    }
    write_meta(meta)
    (RUNS / run_id / "input.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    QUEUE.submit(run_id)
    return meta


def delete_run(run_id: str) -> None:
    d = run_dir(run_id)
    if read_meta(run_id)["status"] in ACTIVE:
        raise ValueError("cancel the run before deleting it")
    for p in sorted(d.rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    d.rmdir()


def mark_interrupted() -> None:
    """A run the previous console process was executing cannot be resumed."""
    for m in list_runs():
        if m["status"] in ACTIVE:
            update_meta(m["id"], status="interrupted", finished_at=now(),
                        error="console restarted while this run was active")


# ---------------------------------------------------------------- Gym stack

class Stack:
    """The `gym env start` process for one config. One stack at a time."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen[bytes] | None = None
        self.config: str | None = None
        self.state = "stopped"  # stopped | starting | ready | failed
        self.since = now()
        self.error: str | None = None
        self.log = RUNS / ".stack.log"
        self._lock = threading.Lock()

    def status(self) -> dict[str, Any]:
        if self.proc and self.proc.poll() is not None and self.state in ("starting", "ready"):
            self._set("failed", f"gym env start exited with code {self.proc.returncode}")
        return {"state": self.state, "config": self.config, "since": self.since, "error": self.error}

    def _set(self, state: str, error: str | None = None) -> None:
        self.state, self.error, self.since = state, error, now()

    def ensure(self, config: str, cancelled: threading.Event, timeout: float = 900, caller: str | None = None) -> None:
        paths = [f"configs/{config}.yaml"] + ([f"configs/users/{caller}.yaml"] if caller else [])
        key = "+".join([config] + ([caller] if caller else []))
        with self._lock:
            if self.status()["state"] == "ready" and self.config == key:
                return
            self._stop_locked()
            RUNS.mkdir(exist_ok=True)
            log = self.log.open("wb")
            self.proc = subprocess.Popen(
                [str(BIN / "gym"), "env", "start", f"+config_paths=[{','.join(paths)}]",
                 "++skip_venv_if_present=true"],
                cwd=REPO, env=subprocess_env(), stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            self.config = key
            self._set("starting")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if cancelled.is_set():
                raise RuntimeError("cancelled while the stack was starting")
            if self.proc.poll() is not None:
                self._set("failed", f"gym env start exited with code {self.proc.returncode}")
                raise RuntimeError(f"{self.error}; see the stack log")
            if READY_RE.search(self.log.read_text(errors="replace")):  # Gym prints a long server table after it
                self._set("ready")
                return
            time.sleep(1)
        self.stop()
        raise RuntimeError(f"stack not ready after {timeout:.0f}s")

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=30)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        # Ray workers outlive the CLI; also clears a stack started outside the console.
        subprocess.run([str(BIN / "ray"), "stop", "--force"], env=subprocess_env(),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        self.proc = None
        self._set("stopped")


STACK = Stack()
TOOL_SERVERS = ToolServers()  # oracle replays; Gym runs use the stack's own


# ---------------------------------------------------------------- queue

class Queue:
    """Executes runs in submission order on one worker thread."""

    def __init__(self) -> None:
        self.pending: deque[str] = deque()
        self.current: str | None = None
        self.cancel = threading.Event()
        self._child: subprocess.Popen[bytes] | None = None
        self._cv = threading.Condition()
        threading.Thread(target=self._loop, name="micol-runs", daemon=True).start()

    def submit(self, run_id: str) -> None:
        with self._cv:
            self.pending.append(run_id)
            self._cv.notify()

    def cancel_run(self, run_id: str) -> None:
        with self._cv:
            if run_id in self.pending:
                self.pending.remove(run_id)
                update_meta(run_id, status="cancelled", finished_at=now())
                return
            if run_id != self.current:
                raise ValueError("run is not active")
            self.cancel.set()
            if self._child and self._child.poll() is None:
                os.killpg(self._child.pid, signal.SIGTERM)

    def _loop(self) -> None:
        while True:
            with self._cv:
                while not self.pending:
                    self._cv.wait()
                self.current = self.pending.popleft()
                self.cancel.clear()
            run_id = self.current
            try:
                meta = read_meta(run_id)
                if meta["kind"] == "oracle":
                    self._oracle(meta)
                else:
                    self._gym(meta)
                status = "cancelled" if self.cancel.is_set() else "done"
                update_meta(run_id, status=status, finished_at=now())
            except Exception as exc:  # noqa: BLE001 - surfaced on the run
                status = "cancelled" if self.cancel.is_set() else "failed"
                update_meta(run_id, status=status, finished_at=now(), error=str(exc))
            finally:
                self.current = None

    def _gym(self, meta: dict[str, Any]) -> None:
        run_id, d = meta["id"], RUNS / meta["id"]
        update_meta(run_id, status="starting", started_at=now())
        STACK.ensure(meta["config"], self.cancel, caller=meta.get("caller"))
        update_meta(run_id, status="running")
        with (d / "eval.log").open("wb") as log:
            self._child = subprocess.Popen(
                [str(BIN / "gym"), "eval", "run", "--no-serve", "+agent_name=micol_agent",
                 f"+input_jsonl_fpath=runs/{run_id}/input.jsonl",
                 f"+output_jsonl_fpath=runs/{run_id}/rollouts.jsonl",
                 "+limit=null", f"+num_samples_in_parallel={int(meta['concurrency'])}",
                 f"+num_repeats={int(meta.get('repeats') or 1)}"],
                cwd=REPO, env=subprocess_env(), stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            code = self._child.wait()
        self._child = None
        if code != 0 and not self.cancel.is_set():
            raise RuntimeError(f"gym eval run exited with code {code}; see the run log")

    def _oracle(self, meta: dict[str, Any]) -> None:
        run_id, d = meta["id"], RUNS / meta["id"]
        update_meta(run_id, status="running", started_at=now())
        rows = [json.loads(line) for line in (d / "input.jsonl").read_text().splitlines()]
        jobs = [(row, a) for row in rows for a in range(int(meta.get("repeats") or 1))]
        with (d / "rollouts.jsonl").open("a") as out, (d / "eval.log").open("a") as log:
            for i, (row, attempt) in enumerate(jobs, 1):
                if self.cancel.is_set():
                    return
                record = {**oracle_record(row), ATTEMPT: attempt}
                out.write(json.dumps(record) + "\n")
                out.flush()
                verdict = "pass" if record["conjunctive"] else "FAIL"
                log.write(f"[{i}/{len(jobs)}] {row['industry']} {row['case_key']} #{attempt + 1}: {verdict}\n")
                log.flush()


def oracle_record(row: dict[str, Any]) -> dict[str, Any]:
    """Replay a task's answer key and score it, in the same shape Gym writes a rollout."""
    session = Session(row["industry"], row["case_key"], TOOL_SERVERS.for_task(row["industry"], row["case_key"]))
    try:
        oracle_replay(session)
        result, scored = session.score()
    finally:
        session.close()
    return {
        **{k: row.get(k) for k in ("industry", "case_key", "category", "difficulty")},
        **verify.reward_file(scored),
        "conjunctive": scored["conjunctive"],
        "components": scored["components"],
        **{k: result[k] for k in ("transcript", "trace", "system_prompt_swaps", "final_state", "ended_by")},
    }


QUEUE = Queue()
