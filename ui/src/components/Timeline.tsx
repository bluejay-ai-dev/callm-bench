import { useState } from "react";
import { ArrowRightLeft, ChevronDown, ChevronRight, Wrench } from "lucide-react";
import type { RolloutView, TimelineEvent, ToolRow } from "@/api";
import { Badge, Mono } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

const compact = (v: unknown) => {
  const s = JSON.stringify(v ?? {});
  return s === "{}" ? "" : s;
};

/** The call in order: what each side said, every tool call with its result, and every agent switch. */
export function Timeline({ view }: { view: RolloutView }) {
  const rowFor = new Map(view.grading.tool_rows.filter((r) => r.actual_index !== null).map((r) => [r.actual_index!, r]));
  const swaps = view.rollout.system_prompt_swaps ?? [];
  const start = swaps[0]?.agent;

  if (!view.timeline.length) {
    return <p className="p-4 text-sm text-muted-foreground">Nothing happened on this call.</p>;
  }
  const hasMessages = view.timeline.some((e) => e.kind === "message");
  return (
    <div className="space-y-2 p-4">
      {start && <AgentMarker agent={start} prompt={swaps[0]?.system_prompt} first />}
      {!hasMessages && (
        <p className="text-xs text-muted-foreground">No conversation: the oracle replays the answer key's tool calls directly.</p>
      )}
      {view.timeline.map((e, i) => (
        <Event key={i} e={e} row={e.kind === "tool" ? rowFor.get(e.index) : undefined}
          prompt={e.kind === "handoff" ? swaps.find((s) => s.agent === e.agent)?.system_prompt : undefined} />
      ))}
      <p className="pt-2 text-center text-xs text-muted-foreground">
        call ended by {view.rollout.ended_by ?? "?"}
        {view.rollout.failure_kind ? ` · rollout error: ${view.rollout.failure_kind}` : ""}
      </p>
    </div>
  );
}

function AgentMarker({ agent, prompt, first }: { agent: string; prompt?: string; first?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="py-1">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 text-xs text-info">
        <span className="h-px flex-1 bg-info/30" />
        <ArrowRightLeft className="size-3.5" />
        <span className="font-medium">{first ? `starts with ${agent}` : `handed off to ${agent}`}</span>
        {prompt && (open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />)}
        <span className="h-px flex-1 bg-info/30" />
      </button>
      {open && prompt && <Mono className="mt-2 max-h-96">{prompt}</Mono>}
    </div>
  );
}

function Event({ e, row, prompt }: { e: TimelineEvent; row?: ToolRow; prompt?: string }) {
  const [open, setOpen] = useState(false);
  if (e.kind === "handoff") return <AgentMarker agent={e.agent} prompt={prompt} />;
  if (e.kind === "message") {
    const agent = e.role === "agent";
    if (e.dropped) {
      // speech the recognizer dropped: the agent never saw it, the caller spoke again
      return (
        <div className="flex justify-end">
          <div className="max-w-[80%] px-3 py-1 text-right text-xs text-muted-foreground italic">
            Not transcribed, the agent heard nothing. Caller said: “{e.said}”
          </div>
        </div>
      );
    }
    return (
      <div className={cn("flex", agent ? "justify-start" : "justify-end")}>
        <div className={cn("max-w-[80%] rounded-lg px-3 py-2", agent ? "bg-muted" : "bg-info-soft")}>
          <div className="mb-0.5 text-[10px] font-semibold tracking-wide text-muted-foreground uppercase">
            {agent ? "agent" : "caller"}
          </div>
          <div className="text-sm leading-relaxed whitespace-pre-wrap">{e.text}</div>
          {e.said && e.said !== e.text && (
            <div className="mt-1 text-xs text-muted-foreground">said: {e.said}</div>
          )}
        </div>
      </div>
    );
  }
  const refused = e.ok === false;
  const matched = row?.status === "match";
  const failing = row && row.status !== "match" && row.status !== "extra";
  return (
    <div className={cn("rounded-md border bg-card text-sm", failing && "border-fail/50", matched && "border-pass/40")}>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left">
        {open ? <ChevronDown className="size-3.5 shrink-0" /> : <ChevronRight className="size-3.5 shrink-0" />}
        <Wrench className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="font-mono font-medium">{e.name}</span>
        <span className="truncate font-mono text-xs text-muted-foreground">{compact(e.parameters)}</span>
        <span className="ml-auto flex shrink-0 items-center gap-1">
          {e.agent && <Badge tone="outline">{e.agent}</Badge>}
          {refused ? <Badge tone="warn">{e.error_code ?? "refused"}</Badge> : <Badge tone="pass">ok</Badge>}
          {matched && <Badge tone="pass">expected #{row.expected_index! + 1}</Badge>}
          {failing && <Badge tone="fail">{row.status === "forbidden" ? "forbidden" : `differs from expected #${row.expected_index! + 1}`}</Badge>}
        </span>
      </button>
      {open && (
        <div className="grid gap-2 border-t p-2.5 md:grid-cols-2">
          <div>
            <div className="mb-1 text-xs text-muted-foreground">arguments</div>
            <Mono>{JSON.stringify(e.parameters ?? {}, null, 2)}</Mono>
          </div>
          <div>
            <div className="mb-1 text-xs text-muted-foreground">server reply</div>
            <Mono className="max-h-80">{e.result === undefined ? "not recorded" : JSON.stringify(e.result, null, 2)}</Mono>
          </div>
        </div>
      )}
    </div>
  );
}
