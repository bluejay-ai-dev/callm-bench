import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api, groupByTask, taskHash, type RolloutView, type TaskGroup } from "@/api";
import { Grading } from "@/components/Grading";
import { Checks, TaskTags } from "@/components/shared";
import { TaskBrief } from "@/components/TaskBrief";
import { Timeline } from "@/components/Timeline";
import { Badge, Button, Card, CardHeader } from "@/components/ui/primitives";
import { cn, go } from "@/lib/utils";

/** One task inside a run: all k attempts side by side, and the selected attempt in full. */
export function RolloutPage({ runId, industry, caseKey, attempt }: { runId: string; industry: string; caseKey: string; attempt: number }) {
  const [view, setView] = useState<RolloutView | null>(null);
  const [groups, setGroups] = useState<TaskGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"grading" | "task">("grading");

  useEffect(() => {
    setView(null);
    setError(null);
    api.rollout(runId, industry, caseKey, attempt).then(setView, (e) => setError(e.message));
  }, [runId, industry, caseKey, attempt]);
  useEffect(() => void api.run(runId).then((r) => setGroups(groupByTask(r.rows))), [runId]);

  const at = groups.findIndex((g) => g.industry === industry && g.case_key === caseKey);
  const me = groups[at];
  const k = me?.attempts.length ?? view?.attempts?.length ?? 1;
  const openTask = (g: TaskGroup, failingFirst: boolean) => {
    const pick = failingFirst ? (g.attempts.find((a) => !a.passed) ?? g.attempts[0]) : g.attempts[0];
    go(taskHash(runId, g.industry, g.case_key, pick.attempt));
  };
  const step = (dir: 1 | -1, failingOnly: boolean) => {
    for (let i = at + dir; i >= 0 && i < groups.length; i += dir) {
      if (!failingOnly || groups[i].passed < groups[i].attempts.length) return openTask(groups[i], failingOnly);
    }
  };
  const attempts = useMemo(() => me?.attempts ?? view?.attempts ?? [], [me, view]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div>
          <button className="text-xs text-muted-foreground hover:underline" onClick={() => go(`#/run/${runId}`)}>
            ← Run
          </button>
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            <span className="font-normal text-muted-foreground">{industry}</span>
            <span className="font-mono">{view?.tag}</span>
            {view?.task?.task_name}
            {me && (
              <Badge tone={me.passed === k ? "pass" : me.passed === 0 ? "fail" : "warn"}>
                {k > 1 ? `${me.passed}/${k} attempts pass` : me.passed ? "pass" : "fail"}
              </Badge>
            )}
          </h1>
          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">{caseKey} <TaskTags metadata={view?.task?.metadata} /></div>
        </div>
        <div className="ml-auto flex items-center gap-1">
          <Button size="xs" variant="outline" onClick={() => step(-1, true)} title="Previous task with a failing attempt">
            <ChevronLeft /> prev failing
          </Button>
          <Button size="xs" variant="outline" onClick={() => step(-1, false)} title="Previous task">
            <ChevronLeft />
          </Button>
          <span className="px-1 text-xs text-muted-foreground tabular-nums">
            task {at + 1}/{groups.length}
          </span>
          <Button size="xs" variant="outline" onClick={() => step(1, false)} title="Next task">
            <ChevronRight />
          </Button>
          <Button size="xs" variant="outline" onClick={() => step(1, true)} title="Next task with a failing attempt">
            next failing <ChevronRight />
          </Button>
          <Button size="xs" variant="ghost" onClick={() => go(`#/task/${industry}/${caseKey}`)}>
            Task history
          </Button>
        </div>
      </div>

      {attempts.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          {attempts.map((a) => (
            <button
              key={a.attempt}
              onClick={() => go(taskHash(runId, industry, caseKey, a.attempt))}
              className={cn(
                "flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-left text-xs transition-colors hover:bg-accent/60",
                a.attempt === attempt && "border-info ring-2 ring-info/30",
              )}
            >
              <span className="font-semibold">Attempt {a.attempt + 1}</span>
              {a.failure_kind ? (
                <Badge tone="warn">error</Badge>
              ) : (
                <Badge tone={a.passed ? "pass" : "fail"}>{a.passed ? "pass" : "fail"}</Badge>
              )}
              <Checks tools={a.tools} handoffs={a.handoffs} db={a.db} size="xs" />
              <span className="text-muted-foreground tabular-nums">
                {a.turns} turns · {a.tool_calls} calls
              </span>
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-sm text-fail">{error}</p>}
      {view && (
        <div className="grid items-start gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <Card className="lg:sticky lg:top-16 lg:max-h-[calc(100vh-5rem)] lg:overflow-auto">
            <CardHeader title={k > 1 ? `The call · attempt ${attempt + 1} of ${k}` : "The call"} />
            <Timeline view={view} />
          </Card>
          <div className="space-y-3">
            <div className="flex gap-1 rounded-lg border bg-card p-1">
              {(["grading", "task"] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)} className={cn("flex-1 rounded-md py-1.5 text-sm font-medium", tab === t ? "bg-accent" : "text-muted-foreground")}>
                  {t === "grading" ? `Grading${k > 1 ? ` · attempt ${attempt + 1}` : ""}` : "Task definition"}
                </button>
              ))}
            </div>
            {tab === "grading" ? <Grading view={view} /> : view.task && <TaskBrief task={view.task} />}
          </div>
        </div>
      )}
    </div>
  );
}
