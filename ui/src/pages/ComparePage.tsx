import { useEffect, useState } from "react";
import { api, taskHash, type CompareView } from "@/api";
import { AttemptDots } from "@/components/shared";
import { Card, Select, Td, Th } from "@/components/ui/primitives";
import { cn, go, pct } from "@/lib/utils";

/** Tasks down, runs across: where runs agree, and the tasks one run passes and another fails. */
export function ComparePage({ ids }: { ids: string[] }) {
  const [d, setD] = useState<CompareView | null>(null);
  const [only, setOnly] = useState<"all" | "differ">("differ");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => void api.compare(ids).then(setD, (e) => setError(e.message)), [ids.join(",")]);
  if (error) return <p className="text-sm text-fail">{error}</p>;
  if (!d) return null;
  const differs = (cells: CompareView["tasks"][number]["cells"]) => {
    const rates = d.runs
      .map((r) => cells[r.id])
      .filter((a) => a?.length)
      .map((a) => a.filter((x) => x.passed).length / a.length);
    return rates.length >= 2 && new Set(rates).size > 1;
  };
  const rows = d.tasks.filter((t) => only === "all" || differs(t.cells));
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div>
          <button className="text-xs text-muted-foreground hover:underline" onClick={() => go("#/")}>
            ← Runs
          </button>
          <h1 className="text-xl font-semibold">Compare {d.runs.length} runs</h1>
        </div>
        <Select className="ml-auto" value={only} onChange={(e) => setOnly(e.target.value as "all" | "differ")}>
          <option value="differ">tasks where runs disagree ({d.tasks.filter((t) => differs(t.cells)).length})</option>
          <option value="all">all tasks ({d.tasks.length})</option>
        </Select>
      </div>
      {rows.length === 0 && (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          The runs agree on every task they share ({d.tasks.filter((t) => Object.keys(t.cells).length >= 2).length}). Switch to
          all tasks to see them.
        </p>
      )}
      <Card className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <Th>Task</Th>
              {d.runs.map((r) => (
                <Th key={r.id} className="cursor-pointer text-center hover:underline" onClick={() => go(`#/run/${r.id}`)}>
                  <div className="font-medium text-foreground">{r.label || r.id}</div>
                  <div>
                    {r.kind === "oracle" ? "oracle" : r.config} · {pct(r.summary.all.passed, r.summary.all.n)}
                  </div>
                </Th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((t) => (
              <tr key={t.key}>
                <Td>
                  <span className="text-xs text-muted-foreground">{t.industry} </span>
                  <button className="font-mono font-medium hover:underline" onClick={() => go(`#/task/${t.industry}/${t.case_key}`)}>
                    {t.tag}
                  </button>{" "}
                  <span className="text-xs">{t.title}</span>
                  <span className="ml-1 font-mono text-[10px] text-muted-foreground">{t.case_key}</span>
                </Td>
                {d.runs.map((r) => {
                  const c = t.cells[r.id];
                  const passed = c?.filter((a) => a.passed).length ?? 0;
                  return (
                    <Td key={r.id} className="text-center">
                      {c?.length ? (
                        <span className="inline-flex items-center gap-2">
                          <button
                            onClick={() => go(taskHash(r.id, t.industry, t.case_key))}
                            className={cn(
                              "rounded px-2 py-0.5 text-xs font-medium tabular-nums",
                              passed === c.length ? "bg-pass-soft text-pass" : passed === 0 ? "bg-fail-soft text-fail" : "bg-warn-soft text-warn",
                            )}
                          >
                            {c.length > 1 ? `${passed}/${c.length}` : passed ? "pass" : "fail"}
                          </button>
                          {c.length > 1 && <AttemptDots attempts={c} onOpen={(a) => go(taskHash(r.id, t.industry, t.case_key, a))} />}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">not run</span>
                      )}
                    </Td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
