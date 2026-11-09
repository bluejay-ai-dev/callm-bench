import { useState } from "react";
import { ArrowRight, ChevronDown, ChevronRight } from "lucide-react";
import type { Task } from "@/api";
import { Badge, Card, CardHeader, Mono } from "@/components/ui/primitives";

/** What the task asks for: the caller's brief and the answer key the grader checks against. */
export function TaskBrief({ task }: { task: Task }) {
  return (
    <div className="space-y-3">
      <Card>
        <CardHeader title="Caller brief (what the simulator is told)" />
        <div className="space-y-3 p-3 text-sm">
          <p className="leading-relaxed whitespace-pre-wrap">{task.intent}</p>
          <div className="flex flex-wrap gap-1.5">
            {task.traits?.map((t) => (
              <Badge key={t.trait_name} tone="outline">
                {t.trait_name}: <span className="font-mono text-foreground">{t.value}</span>
              </Badge>
            ))}
          </div>
          {!!task.scripted_responses?.length && (
            <Fold title={`${task.scripted_responses.length} scripted replies`}>
              <div className="divide-y text-xs">
                {task.scripted_responses.map((s, i) => (
                  <div key={i} className="grid gap-1 py-2 md:grid-cols-2">
                    <span className="text-muted-foreground">when the agent {s.match_phrase}</span>
                    <span>“{s.response_value}”</span>
                  </div>
                ))}
              </div>
            </Fold>
          )}
        </div>
      </Card>
      <Card>
        <CardHeader title="Answer key" />
        <div className="space-y-3 p-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-24 text-muted-foreground">handoff path</span>
            {task.exp_handoff_path.length ? (
              task.exp_handoff_path.map((h, i) => (
                <span key={i} className="flex items-center gap-1">
                  {i > 0 && <ArrowRight className="size-3 text-muted-foreground" />}
                  <span className="rounded bg-muted px-1.5 py-0.5 font-mono">{h.replace("transfer_to_", "")}</span>
                </span>
              ))
            ) : (
              <span className="text-muted-foreground">no transfer required</span>
            )}
          </div>
          <div>
            <div className="mb-1 text-muted-foreground">expected tool calls ({task.exp_tool_calls.length})</div>
            <ol className="space-y-1">
              {task.exp_tool_calls.map((c, i) => (
                <li key={i} className="rounded border px-2 py-1.5">
                  <span className="font-mono font-medium">
                    {i + 1}. {c.name}
                  </span>
                  {c.parameters && Object.keys(c.parameters).length > 0 && (
                    <span className="ml-2 font-mono break-all text-muted-foreground">{JSON.stringify(c.parameters)}</span>
                  )}
                  {c.output && <Badge tone="warn" className="ml-2">must return {String(c.output.error_code ?? "ok")}</Badge>}
                  {c.oracle_parameters && (
                    <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                      oracle uses (not graded): {JSON.stringify(c.oracle_parameters)}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </div>
          {task.exp_db_state && (
            <Fold title="expected final database">
              <Mono className="max-h-96">{JSON.stringify(task.exp_db_state, null, 2)}</Mono>
            </Fold>
          )}
        </div>
      </Card>
    </div>
  );
}

function Fold({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button className="flex items-center gap-1 text-xs font-medium" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />} {title}
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}
