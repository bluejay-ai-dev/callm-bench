import { useState } from "react";
import { ArrowRight, Check, ChevronDown, ChevronRight, X } from "lucide-react";
import type { ArgStatus, Grading as G, RolloutView, ToolRow } from "@/api";
import { Badge, Card, CardHeader, Mono } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

const fmt = (v: unknown) => (typeof v === "number" ? v.toFixed(2) : "–");

/** Why this rollout passed or failed: each check with the evidence the grader used. */
export function Grading({ view }: { view: RolloutView }) {
  const g = view.grading;
  const comp = g.components;
  const passed = (k: string) => Boolean(comp[k]?.passed);
  const overall = g.scores.conjunctive === 1;
  return (
    <div className="space-y-3">
      <Card className={cn("p-4", overall ? "bg-pass-soft/50" : "bg-fail-soft/50")}>
        <div className="flex items-center gap-3">
          <span className={cn("text-lg font-semibold", overall ? "text-pass" : "text-fail")}>
            {overall ? "PASS" : "FAIL"}
          </span>
          <span className="text-xs text-muted-foreground">CALLM score = tools AND handoffs AND final database</span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
          <Score label="Tool calls" ok={passed("tool_adherence")} sub={`reward ${fmt(g.scores.tool_reward)}`} />
          <Score label="Handoffs" ok={passed("handoff_adherence")} sub={`reward ${fmt(g.scores.handoff_reward)}`} />
          <Score label="Final database" ok={passed("state_adherence")} sub={`reward ${fmt(g.scores.state_reward)}`} />
        </div>
        <div className="mt-2 text-xs text-muted-foreground">partial-credit (shaped) score {fmt(g.scores.shaped)}</div>
      </Card>
      <ToolCalls g={g} />
      <Handoffs g={g} ok={passed("handoff_adherence")} verdict={String(comp.handoff_adherence?.verdict ?? "")} />
      <Database g={g} ok={passed("state_adherence")} />
    </div>
  );
}

function Score({ label, ok, sub }: { label: string; ok: boolean; sub: string }) {
  return (
    <div className="rounded-md border bg-card px-2.5 py-2">
      <div className="flex items-center gap-1.5 font-medium">
        {ok ? <Check className="size-3.5 text-pass" /> : <X className="size-3.5 text-fail" />}
        {label}
      </div>
      <div className="mt-0.5 text-muted-foreground">{sub}</div>
    </div>
  );
}

const ROW_BADGE: Record<ToolRow["status"], { label: string; tone: "pass" | "fail" | "neutral" }> = {
  match: { label: "Match", tone: "pass" },
  params_differ: { label: "Arguments differ", tone: "fail" },
  output_differs: { label: "Result differs", tone: "fail" },
  params_and_output_differ: { label: "Arguments & result differ", tone: "fail" },
  missing: { label: "Missing in actual", tone: "fail" },
  extra: { label: "Extra (not required)", tone: "neutral" },
  forbidden: { label: "Forbidden", tone: "fail" },
};

const show = (v: unknown) => (v === undefined || v === null ? "" : typeof v === "string" ? v : JSON.stringify(v));

const ARG_NOTE: Record<ArgStatus, string> = {
  match: "",
  differs: "differs",
  missing: "not passed",
  default: "omitted; the default matches",
  prose: "free text: only checked to be non-empty",
  empty: "free text left empty",
  ignored: "not graded",
  unchecked: "not checked",
};

function ArgTable({ row }: { row: ToolRow }) {
  if (!row.args.length) return <p className="text-xs text-muted-foreground">No arguments.</p>;
  return (
    <table className="w-full table-fixed text-xs">
      <thead>
        <tr className="text-left text-muted-foreground">
          <th className="w-[22%] pb-1 font-medium">argument</th>
          <th className="w-[39%] pb-1 font-medium">expected</th>
          <th className="w-[39%] pb-1 font-medium">actual</th>
        </tr>
      </thead>
      <tbody className="font-mono">
        {row.args.map((a) => {
          const bad = a.status === "differs" || a.status === "missing" || a.status === "empty";
          const muted = a.status === "unchecked" || a.status === "ignored" || a.status === "prose";
          return (
            <tr key={a.key} className={cn("align-top", bad && "bg-fail-soft", muted && "text-muted-foreground")}>
              <td className="py-1 pr-2 break-all">{a.key}</td>
              <td className="py-1 pr-2 break-all">{a.expected === null || a.expected === undefined ? <span className="text-muted-foreground">–</span> : show(a.expected)}</td>
              <td className="py-1 break-all">
                {a.present ? show(a.actual) : <span className="text-muted-foreground">–</span>}
                {ARG_NOTE[a.status] && (
                  <span className={cn("block font-sans text-[10px]", bad ? "text-fail" : "text-muted-foreground")}>
                    {ARG_NOTE[a.status]}
                  </span>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

const outcomeText = (o: { ok?: boolean; error_code?: string } | null, side: "expected" | "actual") =>
  !o ? (side === "expected" ? "any" : "–") : o.error_code ? `refused: ${o.error_code}` : o.ok === false ? "refused" : "ok";

function ToolRowItem({ row }: { row: ToolRow }) {
  const [open, setOpen] = useState(row.status !== "match" && row.status !== "extra");
  const badge = ROW_BADGE[row.status];
  const [reply, setReply] = useState(false);
  return (
    <div className="px-3 py-2">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 text-left text-xs">
        {open ? <ChevronDown className="size-3.5 shrink-0" /> : <ChevronRight className="size-3.5 shrink-0" />}
        {row.status === "match" ? (
          <Check className="size-4 shrink-0 text-pass" />
        ) : row.status === "extra" ? (
          <span className="size-4 shrink-0 text-center text-muted-foreground">·</span>
        ) : (
          <X className="size-4 shrink-0 text-fail" />
        )}
        <span className="w-12 shrink-0 text-muted-foreground tabular-nums">
          {row.actual_index !== null ? `call ${row.actual_index + 1}` : "never"}
        </span>
        <span className="truncate font-mono font-medium">{row.name}</span>
        {row.agent && <Badge tone="outline">{row.agent}</Badge>}
        <span className="ml-auto flex shrink-0 items-center gap-1.5">
          {row.expected_index !== null && <span className="text-muted-foreground">expected #{row.expected_index + 1}</span>}
          <Badge tone={badge.tone}>{badge.label}</Badge>
        </span>
      </button>
      {open && (
        <div className="mt-2 ml-6 space-y-2 rounded-md border bg-muted/30 p-2.5">
          <ArgTable row={row} />
          <table className="w-full table-fixed text-xs">
            <tbody>
              <tr className={cn("align-top", !row.outcome.match && "bg-fail-soft")}>
                <td className="w-[22%] py-1 pr-2 text-muted-foreground">result</td>
                <td className="w-[39%] py-1 pr-2">{outcomeText(row.outcome.expected, "expected")}</td>
                <td className="w-[39%] py-1">
                  {row.actual_index === null ? "–" : outcomeText(row.outcome.actual, "actual")}
                  {row.reply !== undefined && row.reply !== null && (
                    <button className="ml-2 text-info hover:underline" onClick={() => setReply(!reply)}>
                      {reply ? "hide reply" : "server reply"}
                    </button>
                  )}
                </td>
              </tr>
            </tbody>
          </table>
          {reply && <Mono className="max-h-60">{JSON.stringify(row.reply, null, 2)}</Mono>}
        </div>
      )}
    </div>
  );
}

function ToolCalls({ g }: { g: G }) {
  const n = (s: ToolRow["status"][]) => g.tool_rows.filter((r) => s.includes(r.status)).length;
  const matched = n(["match"]);
  return (
    <Card>
      <CardHeader title="Tool calls">
        <Badge tone={g.components.tool_adherence?.passed ? "pass" : "fail"}>
          {g.components.tool_adherence?.passed ? "pass" : "fail"}
        </Badge>
      </CardHeader>
      <div className="flex flex-wrap gap-x-4 gap-y-1 border-b px-3 py-2 text-xs text-muted-foreground">
        <span>expected <b className="text-foreground">{g.expected_count}</b></span>
        <span>actual <b className="text-foreground">{g.actual_count}</b></span>
        <span>matched <b className="text-pass">{matched}/{g.expected_count}</b></span>
        <span>differ <b className="text-fail">{n(["params_differ", "output_differs", "params_and_output_differ"])}</b></span>
        <span>missing <b className="text-fail">{n(["missing"])}</b></span>
        <span>extra <b className="text-foreground">{n(["extra"])}</b></span>
        {n(["forbidden"]) > 0 && <span>forbidden <b className="text-fail">{n(["forbidden"])}</b></span>}
      </div>
      <p className="px-3 pt-2 text-[11px] text-muted-foreground">
        In the order the agent made them; expected calls it never made come last. Extra calls are allowed unless forbidden.
      </p>
      <div className="divide-y">
        {g.tool_rows.length === 0 && <p className="p-3 text-xs text-muted-foreground">No calls expected or made.</p>}
        {g.tool_rows.map((row, i) => (
          <ToolRowItem key={`${row.actual_index}-${row.expected_index}-${i}`} row={row} />
        ))}
      </div>
    </Card>
  );
}

function Path({ hops }: { hops: string[] }) {
  if (!hops.length) return <span className="text-muted-foreground">none</span>;
  return (
    <span className="flex flex-wrap items-center gap-1">
      {hops.map((h, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ArrowRight className="size-3 text-muted-foreground" />}
          <span className="rounded bg-muted px-1.5 py-0.5 font-mono">{h.replace("transfer_to_", "")}</span>
        </span>
      ))}
    </span>
  );
}

function Handoffs({ g, ok, verdict }: { g: G; ok: boolean; verdict: string }) {
  return (
    <Card>
      <CardHeader title="Handoff path">
        <Badge tone={ok ? "pass" : "fail"}>{verdict.replaceAll("_", " ") || (ok ? "pass" : "fail")}</Badge>
      </CardHeader>
      <div className="grid grid-cols-[80px_1fr] gap-y-2 p-3 text-xs">
        <span className="text-muted-foreground">expected</span>
        <Path hops={g.handoffs.expected} />
        <span className="text-muted-foreground">actual</span>
        <Path hops={g.handoffs.actual} />
      </div>
    </Card>
  );
}

function Database({ g, ok }: { g: G; ok: boolean }) {
  return (
    <Card>
      <CardHeader title="Final database">
        <Badge tone={ok ? "pass" : "fail"}>{ok ? "matches" : "mismatch"}</Badge>
      </CardHeader>
      <p className="px-3 pt-2 text-xs text-muted-foreground">
        Compared after normalizing: ignored columns and per-industry rules are applied, so "differs" below is a hint and the
        badge is the verdict.
      </p>
      <div className="divide-y">
        {g.db_tables.map((t) => (
          <Table key={t.table} t={t} />
        ))}
      </div>
    </Card>
  );
}

function Table({ t }: { t: G["db_tables"][number] }) {
  const [open, setOpen] = useState(!t.same);
  const count = (v: unknown) => (Array.isArray(v) ? v.length : v ? 1 : 0);
  return (
    <div className="px-3 py-2 text-xs">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2">
        {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
        <span className="font-mono font-medium">{t.table}</span>
        <span className="text-muted-foreground">
          {count(t.expected)} expected · {count(t.actual)} actual rows
        </span>
        <Badge tone={t.same ? "neutral" : "warn"} className="ml-auto">
          {t.same ? "same" : "differs"}
        </Badge>
      </button>
      {open && (
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          <div>
            <div className="mb-1 text-muted-foreground">expected</div>
            <Mono className="max-h-72">{JSON.stringify(t.expected, null, 2)}</Mono>
          </div>
          <div>
            <div className="mb-1 text-muted-foreground">actual</div>
            <Mono className="max-h-72">{JSON.stringify(t.actual, null, 2)}</Mono>
          </div>
        </div>
      )}
    </div>
  );
}
