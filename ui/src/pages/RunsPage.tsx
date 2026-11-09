import { useState } from "react";
import { GitCompare, Plus, RotateCw, Trash2 } from "lucide-react";
import { api, type RunMeta } from "@/api";
import { Bar, StatusBadge, usePoll } from "@/components/shared";
import { Badge, Button, Card, Empty, Td, Th } from "@/components/ui/primitives";
import { ago, duration, go, pct } from "@/lib/utils";

const INDUSTRY_SHORT: Record<string, string> = { healthcare: "HC", legal: "Legal", "customer-support": "CS" };

export function RunsPage() {
  const { data, error, refresh } = usePoll(api.runs, 3000);
  const [picked, setPicked] = useState<string[]>([]);
  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
    } catch (e) {
      alert((e as Error).message);
    }
    refresh();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">Runs</h1>
        <span className="text-sm text-muted-foreground">{data ? `${data.length} total` : ""}</span>
        <div className="ml-auto flex gap-2">
          {picked.length >= 2 && (
            <Button variant="outline" size="sm" onClick={() => go(`#/compare/${picked.join(",")}`)}>
              <GitCompare /> Compare {picked.length}
            </Button>
          )}
          <Button size="sm" onClick={() => go("#/new")}>
            <Plus /> New run
          </Button>
        </div>
      </div>
      {error && <p className="text-sm text-fail">{error}</p>}
      {data && data.length === 0 && <Empty>No runs yet. Start one with New run.</Empty>}
      {data && data.length > 0 && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <Th className="w-8" />
                <Th>Run</Th>
                <Th>Status</Th>
                <Th>Pass rate</Th>
                <Th>By industry</Th>
                <Th>Started</Th>
                <Th>Took</Th>
                <Th />
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.map((r) => (
                <Row key={r.id} r={r} picked={picked.includes(r.id)} onPick={() => toggle(r.id)} act={act} />
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function Row({ r, picked, onPick, act }: { r: RunMeta; picked: boolean; onPick: () => void; act: (f: () => Promise<unknown>) => void }) {
  const s = r.summary.all;
  const active = ["queued", "starting", "running"].includes(r.status);
  return (
    <tr className="cursor-pointer hover:bg-accent/50" onClick={() => go(`#/run/${r.id}`)}>
      <Td onClick={(e) => e.stopPropagation()}>
        <input type="checkbox" checked={picked} onChange={onPick} title="Select to compare" />
      </Td>
      <Td>
        <div className="font-medium">{r.label || r.id}</div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Badge tone={r.kind === "oracle" ? "outline" : "info"}>{r.kind === "oracle" ? "oracle" : r.config}{r.caller ? ` + ${r.caller} caller` : ""}</Badge>
          {r.source && <Badge tone="outline">{String(r.source.factory_run ?? "")} {String(r.source.step ?? "")}</Badge>}
          {r.total / (r.repeats ?? 1)} tasks
          {(r.repeats ?? 1) > 1 && <Badge tone="info">k={r.repeats}</Badge>}
          {r.kind === "gym" ? ` · ${r.concurrency} parallel` : ""}
        </div>
      </Td>
      <Td>
        <StatusBadge status={r.status} />
        {active && <Bar value={r.done} total={r.total} className="mt-1.5 w-28" />}
      </Td>
      <Td>
        <span className="font-semibold tabular-nums">{pct(s.passed, s.n)}</span>
        <span className="ml-1.5 text-xs text-muted-foreground tabular-nums">
          {s.passed}/{s.n}
        </span>
        {s.k > 1 && (
          <div className="text-[11px] text-muted-foreground tabular-nums">
            pass@{s.k} {s.pass_any}/{s.tasks} · pass^{s.k} {s.pass_all}/{s.tasks}
          </div>
        )}
      </Td>
      <Td>
        <div className="flex gap-2 text-xs tabular-nums">
          {Object.entries(r.summary.by_industry).map(([ind, b]) => (
            <span key={ind}>
              <span className="text-muted-foreground">{INDUSTRY_SHORT[ind] ?? ind}</span> {b.passed}/{b.n}
            </span>
          ))}
        </div>
      </Td>
      <Td className="text-xs text-muted-foreground">{ago(r.created_at)}</Td>
      <Td className="text-xs text-muted-foreground tabular-nums">{duration(r.started_at, r.finished_at)}</Td>
      <Td onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-end gap-1">
          {active ? (
            <Button size="xs" variant="outline" onClick={() => act(() => api.cancel(r.id))}>
              Cancel
            </Button>
          ) : (
            <>
              <Button size="icon" variant="ghost" title="Run the same tasks again" onClick={() => act(() => api.rerun(r.id))}>
                <RotateCw />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                title="Delete run"
                onClick={() => confirm(`Delete run ${r.label || r.id} and its rollouts?`) && act(() => api.remove(r.id))}
              >
                <Trash2 />
              </Button>
            </>
          )}
        </div>
      </Td>
    </tr>
  );
}
