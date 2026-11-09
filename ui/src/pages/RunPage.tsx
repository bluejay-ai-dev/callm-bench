import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, RotateCw, Square } from "lucide-react";
import { api, groupByTask, taskHash, type Block, type RunDetail, type TaskGroup } from "@/api";
import { AttemptDots, Bar, StatusBadge, fractionTone, usePoll } from "@/components/shared";
import { Badge, Button, Card, CardHeader, Empty, Input, Mono, Select, Td, Th } from "@/components/ui/primitives";
import { ago, cn, duration, go, pct } from "@/lib/utils";

const ACTIVE = ["queued", "starting", "running"];

export function RunPage({ id }: { id: string }) {
  const [live, setLive] = useState(true);
  const { data: run, error, refresh } = usePoll<RunDetail>(
    () => api.run(id).then((r) => (setLive(ACTIVE.includes(r.status)), r)),
    2000,
    live,
    [id],
  );
  const groups = useMemo(() => groupByTask(run?.rows ?? []), [run]);
  if (error) return <p className="text-sm text-fail">{error}</p>;
  if (!run) return null;
  const active = ACTIVE.includes(run.status);
  const k = run.repeats ?? 1;
  const act = async (fn: () => Promise<unknown>, after?: (r: unknown) => void) => {
    try {
      const r = await fn();
      after?.(r);
    } catch (e) {
      alert((e as Error).message);
    }
    setLive(true);
    refresh();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start gap-3">
        <div>
          <button className="text-xs text-muted-foreground hover:underline" onClick={() => go("#/")}>
            ← Runs
          </button>
          <h1 className="text-xl font-semibold">{run.label || run.id}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <StatusBadge status={run.status} />
            <Badge tone={run.kind === "oracle" ? "outline" : "info"}>{run.kind === "oracle" ? "oracle replay" : `configs/${run.config}.yaml`}</Badge>
            {run.caller && <Badge tone="outline">caller {run.caller}</Badge>}
            {run.source && <Badge tone="outline">{Object.entries(run.source).map(([k, v]) => `${k} ${v}`).join(" · ")}</Badge>}
            <span>{run.total / k} tasks</span>
            {k > 1 && <Badge tone="info">k = {k} attempts each</Badge>}
            {run.kind === "gym" && <span>· {run.concurrency} in parallel</span>}
            <span>· created {ago(run.created_at)}</span>
            <span>· took {duration(run.started_at, run.finished_at)}</span>
            <span className="font-mono">· {run.id}</span>
          </div>
        </div>
        <div className="ml-auto flex gap-2">
          {active ? (
            <Button variant="danger" size="sm" onClick={() => act(() => api.cancel(id))}>
              <Square /> Cancel
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={() => act(() => api.rerun(id), (r) => go(`#/run/${(r as RunDetail).id}`))}>
              <RotateCw /> Run again
            </Button>
          )}
        </div>
      </div>

      {active && (
        <Card className="p-4">
          <div className="mb-1.5 flex text-xs">
            <span>{run.status === "starting" ? "Starting the Gym servers…" : run.status === "queued" ? "Waiting for the run ahead of it" : "Rollouts"}</span>
            <span className="ml-auto tabular-nums text-muted-foreground">
              {run.done}/{run.total}
            </span>
          </div>
          <Bar value={run.done} total={run.total} />
        </Card>
      )}
      {run.error && <Card className="border-fail/40 bg-fail-soft/40 p-3 text-sm text-fail">{run.error}</Card>}

      {run.summary.all.n > 0 && (
        <div className="grid gap-3 md:grid-cols-4">
          <Stat title="All tasks" b={run.summary.all} k={k} />
          {Object.entries(run.summary.by_industry).map(([ind, b]) => (
            <Stat key={ind} title={ind} b={b} k={k} />
          ))}
        </div>
      )}
      {groups.length > 0 ? <Grid groups={groups} runId={id} k={k} /> : !active && <Empty>No rollouts were recorded.</Empty>}
      {groups.length > 0 && <Tasks groups={groups} runId={id} k={k} />}
      <Log id={id} active={active} defaultOpen={active || run.status === "failed"} />
    </div>
  );
}

function Stat({ title, b, k }: { title: string; b: Block; k: number }) {
  return (
    <Card className="p-3">
      <div className="text-xs text-muted-foreground">{title}</div>
      <div className="mt-0.5 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tabular-nums">{pct(b.passed, b.n)}</span>
        <span className="text-xs text-muted-foreground tabular-nums">
          {b.passed}/{b.n} {k > 1 ? "rollouts" : ""} pass
        </span>
      </div>
      {k > 1 && (
        <div className="mt-1.5 grid grid-cols-2 gap-1 text-[11px] tabular-nums">
          <span title="Tasks with at least one passing attempt">
            pass@{k} <b>{b.pass_any}</b>/{b.tasks}
          </span>
          <span title="Tasks where every attempt passed">
            pass^{k} <b>{b.pass_all}</b>/{b.tasks}
          </span>
        </div>
      )}
      <div className="mt-1.5 grid grid-cols-3 gap-1 text-[11px] tabular-nums">
        <span title="Tool calls">T {b.tools}/{b.n}</span>
        <span title="Handoffs">H {b.handoffs}/{b.n}</span>
        <span title="Final database">D {b.db}/{b.n}</span>
      </div>
      <div className="mt-1 text-[11px] text-muted-foreground">
        shaped {b.shaped?.toFixed(2) ?? "–"}
        {b.errors > 0 && <span className="text-fail"> · {b.errors} rollout errors</span>}
      </div>
    </Card>
  );
}

function Grid({ groups, runId, k }: { groups: TaskGroup[]; runId: string; k: number }) {
  const byInd = useMemo(() => {
    const m: Record<string, TaskGroup[]> = {};
    groups.forEach((g) => (m[g.industry] ??= []).push(g));
    return m;
  }, [groups]);
  return (
    <Card>
      <CardHeader title="Every task">
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="size-3 rounded-sm bg-pass" /> {k > 1 ? "all attempts pass" : "pass"}
          {k > 1 && (
            <>
              <span className="size-3 rounded-sm bg-warn" /> some
            </>
          )}
          <span className="size-3 rounded-sm bg-fail" /> {k > 1 ? "none" : "fail"}
        </span>
      </CardHeader>
      <div className="space-y-3 p-3">
        {Object.entries(byInd).map(([ind, gs]) => (
          <div key={ind} className="flex gap-3">
            <div className="w-32 shrink-0 pt-0.5 text-xs text-muted-foreground">{ind}</div>
            <div className="flex flex-wrap gap-1">
              {gs.map((g) => (
                <button
                  key={g.case_key}
                  onClick={() => go(taskHash(runId, g.industry, g.case_key))}
                  title={`${g.tag} ${g.title} (${g.case_key}): ${g.passed}/${g.attempts.length} attempts pass`}
                  className={cn(
                    "flex h-6 items-center justify-center gap-1 rounded px-1.5 font-mono text-[10px] font-medium text-white transition-opacity hover:opacity-80",
                    k > 1 ? "w-[4.5rem]" : "w-14",
                    fractionTone(g.passed, g.attempts.length),
                  )}
                >
                  {g.tag}
                  {k > 1 && <span className="opacity-80">{g.passed}/{g.attempts.length}</span>}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

const share = (g: TaskGroup, key: "tools" | "handoffs" | "db") => g.attempts.filter((a) => a[key]).length;

function Tasks({ groups, runId, k }: { groups: TaskGroup[]; runId: string; k: number }) {
  const [f, setF] = useState({ industry: "", outcome: "", check: "", q: "" });
  const shown = groups.filter((g) => {
    const n = g.attempts.length;
    const outcome =
      !f.outcome ||
      (f.outcome === "all" && g.passed === n) ||
      (f.outcome === "none" && g.passed === 0) ||
      (f.outcome === "some" && g.passed > 0 && g.passed < n) ||
      (f.outcome === "anyfail" && g.passed < n);
    const check = !f.check || share(g, f.check as "tools" | "handoffs" | "db") < n;
    return (!f.industry || g.industry === f.industry) && outcome && check && (!f.q || `${g.case_key} ${g.tag} ${g.title}`.toLowerCase().includes(f.q.toLowerCase()));
  });
  const industries = [...new Set(groups.map((g) => g.industry))];
  const avg = (g: TaskGroup, pick: (a: TaskGroup["attempts"][number]) => number) =>
    g.attempts.reduce((s, a) => s + pick(a), 0) / g.attempts.length;
  return (
    <Card className="overflow-hidden">
      <CardHeader title="Results">
        <Select value={f.industry} onChange={(e) => setF({ ...f, industry: e.target.value })}>
          <option value="">all industries</option>
          {industries.map((i) => <option key={i}>{i}</option>)}
        </Select>
        <Select value={f.outcome} onChange={(e) => setF({ ...f, outcome: e.target.value })}>
          <option value="">any result</option>
          {k > 1 ? (
            <>
              <option value="all">every attempt passed</option>
              <option value="some">flaky (some passed)</option>
              <option value="none">no attempt passed</option>
              <option value="anyfail">any attempt failed</option>
            </>
          ) : (
            <>
              <option value="all">pass</option>
              <option value="none">fail</option>
            </>
          )}
        </Select>
        <Select value={f.check} onChange={(e) => setF({ ...f, check: e.target.value })}>
          <option value="">any check</option>
          <option value="tools">failed tool calls</option>
          <option value="handoffs">failed handoffs</option>
          <option value="db">failed database</option>
        </Select>
        <Input placeholder="case key" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} className="w-28" />
        <span className="text-xs text-muted-foreground">{shown.length}</span>
      </CardHeader>
      <div className="max-h-[520px] overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 border-b bg-card">
            <tr>
              <Th>Task</Th>
              <Th>{k > 1 ? `Attempts (k=${k})` : "Result"}</Th>
              <Th title="Attempts that passed each check">Tools</Th>
              <Th>Handoffs</Th>
              <Th>Database</Th>
              <Th>Shaped</Th>
              <Th>Turns</Th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {shown.map((g) => {
              const n = g.attempts.length;
              const frac = (x: number) => (
                <span className={cn("tabular-nums", x === n ? "text-pass" : x === 0 ? "text-fail" : "text-warn")}>
                  {x}/{n}
                </span>
              );
              return (
                <tr key={`${g.industry}/${g.case_key}`} className="cursor-pointer hover:bg-accent/50" onClick={() => go(taskHash(runId, g.industry, g.case_key))}>
                  <Td>
                    <span className="text-xs text-muted-foreground">{g.industry} </span>
                    <span className="font-mono font-medium">{g.tag}</span> <span>{g.title}</span>
                    <span className="ml-1.5 font-mono text-[10px] text-muted-foreground">{g.case_key}</span>
                  </Td>
                  <Td>
                    <span className="flex items-center gap-2">
                      <AttemptDots attempts={g.attempts} onOpen={(a) => go(taskHash(runId, g.industry, g.case_key, a))} />
                      <span className="text-xs tabular-nums">{g.passed}/{n}</span>
                    </span>
                  </Td>
                  <Td>{frac(share(g, "tools"))}</Td>
                  <Td>{frac(share(g, "handoffs"))}</Td>
                  <Td>{frac(share(g, "db"))}</Td>
                  <Td className="tabular-nums">{avg(g, (a) => a.shaped ?? 0).toFixed(2)}</Td>
                  <Td className="tabular-nums">{avg(g, (a) => a.turns).toFixed(0)}</Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Log({ id, active, defaultOpen }: { id: string; active: boolean; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const { data } = usePoll(() => api.runLog(id), 2000, open && active, [id, open]);
  return (
    <Card>
      <button className="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-semibold" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />} Log
      </button>
      {open && <Mono className="m-3 mt-0 max-h-80 text-[11px]">{data?.log || "No output yet."}</Mono>}
    </Card>
  );
}
