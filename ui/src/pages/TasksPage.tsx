import { useEffect, useState } from "react";
import { FlaskConical, Loader2 } from "lucide-react";
import { api, taskHash, type RolloutView, type TaskDetail, type TaskRow } from "@/api";
import { Grading } from "@/components/Grading";
import { AttemptDots, PassBadge, TaskTags } from "@/components/shared";
import { TaskBrief } from "@/components/TaskBrief";
import { Timeline } from "@/components/Timeline";
import { Badge, Button, Card, CardHeader, Empty, Input, Select, Td, Th } from "@/components/ui/primitives";
import { ago, go } from "@/lib/utils";

export function TasksPage() {
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [f, setF] = useState({ industry: "", difficulty: "", tag: "", q: "" });
  useEffect(() => void api.tasks().then((d) => setTasks(d.tasks)), []);
  const shown = tasks.filter(
    (t) =>
      (!f.industry || t.industry === f.industry) &&
      (!f.difficulty || t.difficulty === f.difficulty) &&
      (!f.tag || (t.tags ?? []).includes(f.tag)) &&
      (!f.q || `${t.case_key} ${t.tag} ${t.name}`.toLowerCase().includes(f.q.toLowerCase())),
  );
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">Tasks</h1>
        <span className="text-sm text-muted-foreground">{shown.length} of {tasks.length}</span>
        <div className="ml-auto flex gap-2">
          <Select value={f.industry} onChange={(e) => setF({ ...f, industry: e.target.value })}>
            <option value="">all industries</option>
            <option>healthcare</option>
            <option>legal</option>
            <option>customer-support</option>
          </Select>
          <Select value={f.difficulty} onChange={(e) => setF({ ...f, difficulty: e.target.value })}>
            <option value="">all difficulties</option>
            {[...new Set(tasks.map((t) => t.difficulty))].map((d) => <option key={d ?? ""}>{d}</option>)}
          </Select>
          <Select value={f.tag} onChange={(e) => setF({ ...f, tag: e.target.value })}>
            <option value="">all tags</option>
            {[...new Set(tasks.flatMap((t) => t.tags ?? []))].sort().map((g) => <option key={g}>{g}</option>)}
          </Select>
          <Input placeholder="search" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} className="w-48" />
        </div>
      </div>
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <Th>Industry</Th>
              <Th>Category</Th>
              <Th>Name</Th>
              <Th>Tags</Th>
              <Th>Difficulty</Th>
              <Th>Expected calls</Th>
              <Th>Handoffs</Th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {shown.map((t) => (
              <tr key={`${t.industry}/${t.case_key}`} className="cursor-pointer hover:bg-accent/50" onClick={() => go(`#/task/${t.industry}/${t.case_key}`)}>
                <Td className="text-xs text-muted-foreground">{t.industry}</Td>
                <Td className="font-mono font-medium whitespace-nowrap">{t.tag}</Td>
                <Td className="max-w-md truncate text-xs">
                  {t.name} <span className="ml-1 font-mono text-[10px] text-muted-foreground">{t.case_key}</span>
                </Td>
                <Td className="whitespace-nowrap">{(t.tags ?? []).map((g) => <Badge key={g} className="mr-1">{g}</Badge>)}</Td>
                <Td><Badge>{t.difficulty}</Badge></Td>
                <Td className="tabular-nums">{t.calls}</Td>
                <Td className="tabular-nums">{t.handoffs}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export function TaskPage({ industry, caseKey }: { industry: string; caseKey: string }) {
  const [d, setD] = useState<TaskDetail | null>(null);
  const [oracle, setOracle] = useState<RolloutView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setOracle(null);
    api.task(industry, caseKey).then(setD, (e) => setError(e.message));
  }, [industry, caseKey]);
  const replay = async () => {
    setBusy(true);
    setError(null);
    try {
      setOracle(await api.oracle(industry, caseKey));
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy(false);
  };
  if (error && !d) return <p className="text-sm text-fail">{error}</p>;
  if (!d) return null;
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2">
        <div>
          <button className="text-xs text-muted-foreground hover:underline" onClick={() => go("#/tasks")}>
            ← Tasks
          </button>
          <h1 className="text-xl font-semibold">
            <span className="font-normal text-muted-foreground">{industry}</span> <span className="font-mono">{d.tag}</span> {d.task.task_name}
          </h1>
          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">{caseKey} <TaskTags metadata={d.task.metadata} /></div>
        </div>
        <Button className="ml-auto" variant="outline" size="sm" onClick={replay} disabled={busy}>
          {busy ? <Loader2 className="animate-spin" /> : <FlaskConical />} Replay answer key
        </Button>
      </div>
      {error && <p className="text-sm text-fail">{error}</p>}
      {oracle && (
        <Card className="p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            Oracle replay <PassBadge passed={oracle.grading.scores.conjunctive === 1} />
            <span className="text-xs font-normal text-muted-foreground">the answer key's calls, run against a fresh database, graded</span>
          </div>
          <div className="grid items-start gap-3 lg:grid-cols-2">
            <Card><Timeline view={oracle} /></Card>
            <Grading view={oracle} />
          </div>
        </Card>
      )}
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        <TaskBrief task={d.task} />
        <div className="space-y-3">
          <Card>
            <CardHeader title="Results across runs" />
            {d.history.length === 0 ? (
              <div className="p-3"><Empty>Not in any run yet.</Empty></div>
            ) : (
              <div className="divide-y">
                {d.history.map((h) => (
                  <button key={h.run.id} onClick={() => go(taskHash(h.run.id, industry, caseKey))} className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent/50">
                    <span className="w-9 shrink-0 font-medium tabular-nums">
                      {h.attempts.filter((a) => a.passed).length}/{h.attempts.length}
                    </span>
                    <AttemptDots attempts={h.attempts} onOpen={(a) => go(taskHash(h.run.id, industry, caseKey, a))} />
                    <span className="truncate">{h.run.label || h.run.id}</span>
                    <span className="ml-auto shrink-0 text-muted-foreground">{h.run.kind === "oracle" ? "oracle" : h.run.config} · {ago(h.run.created_at)}</span>
                  </button>
                ))}
              </div>
            )}
          </Card>
          <Card>
            <CardHeader title="Agents in this industry" />
            <div className="space-y-2 p-3 text-xs">
              {d.agents.map((a) => (
                <div key={a.name}>
                  <span className="font-medium">{a.name}</span>
                  {a.name === d.start && <Badge tone="info" className="ml-1.5">entry</Badge>}
                  <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">{a.tools.join(", ")}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
