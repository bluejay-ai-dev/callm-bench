import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Power } from "lucide-react";
import { api, type Health, type RunStatus } from "@/api";
import { Badge, Button } from "@/components/ui/primitives";
import { ago, cn } from "@/lib/utils";

/** Fetch now, then again every `ms` while `active` is true. */
export function usePoll<T>(load: () => Promise<T>, ms: number, active = true, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadRef = useRef(load);
  loadRef.current = load;
  const refresh = useCallback(() => {
    loadRef.current().then(
      (d) => {
        setData(d);
        setError(null);
      },
      (e: Error) => setError(e.message),
    );
  }, []);
  useEffect(() => {
    refresh();
    if (!active) return;
    const t = setInterval(refresh, ms);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, active, refresh, ...deps]);
  return { data, error, refresh };
}

const STATUS_TONE: Record<RunStatus, "pass" | "fail" | "warn" | "info" | "neutral"> = {
  queued: "neutral",
  starting: "info",
  running: "info",
  done: "pass",
  failed: "fail",
  cancelled: "neutral",
  interrupted: "warn",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  const live = status === "running" || status === "starting";
  return (
    <Badge tone={STATUS_TONE[status]}>
      {live && <Loader2 className="size-3 animate-spin" />}
      {status === "starting" ? "starting servers" : status}
    </Badge>
  );
}

/** A task's metadata.tags, as chips. */
export function TaskTags({ metadata }: { metadata?: Record<string, unknown> }) {
  const tags = Array.isArray(metadata?.tags) ? (metadata.tags as string[]) : [];
  if (!tags.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1 align-middle">
      {tags.map((t) => <Badge key={t} tone="outline">{t}</Badge>)}
    </span>
  );
}

export function PassBadge({ passed }: { passed: boolean }) {
  return <Badge tone={passed ? "pass" : "fail"}>{passed ? "pass" : "fail"}</Badge>;
}

/** The three graded checks as T / H / D chips. */
export function Checks({ tools, handoffs, db, size = "sm" }: { tools: boolean; handoffs: boolean; db: boolean; size?: "sm" | "xs" }) {
  const chip = (label: string, ok: boolean, title: string) => (
    <span
      title={`${title}: ${ok ? "pass" : "fail"}`}
      className={cn(
        "inline-flex items-center justify-center rounded font-mono font-semibold",
        size === "sm" ? "size-5 text-[10px]" : "size-4 text-[9px]",
        ok ? "bg-pass-soft text-pass" : "bg-fail-soft text-fail",
      )}
    >
      {label}
    </span>
  );
  return (
    <span className="inline-flex gap-0.5">
      {chip("T", tools, "Tool calls")}
      {chip("H", handoffs, "Handoffs")}
      {chip("D", db, "Final database")}
    </span>
  );
}

/** One square per attempt, green or red; clicking one opens that attempt. */
export function AttemptDots({ attempts, current, onOpen }: { attempts: RowBriefLike[]; current?: number; onOpen?: (attempt: number) => void }) {
  return (
    <span className="inline-flex flex-wrap gap-0.5">
      {attempts.map((a) => (
        <button
          key={a.attempt}
          onClick={onOpen ? (e) => (e.stopPropagation(), onOpen(a.attempt)) : undefined}
          title={`attempt ${a.attempt + 1}: ${a.failure_kind ? `error (${a.failure_kind})` : a.passed ? "pass" : "fail"}`}
          className={cn(
            "size-3 rounded-sm",
            a.failure_kind ? "bg-muted-foreground" : a.passed ? "bg-pass" : "bg-fail",
            current === a.attempt && "ring-2 ring-info ring-offset-1 ring-offset-background",
            !onOpen && "cursor-default",
          )}
        />
      ))}
    </span>
  );
}

type RowBriefLike = { attempt: number; passed: boolean; failure_kind: string | null };

/** Background for a task cell by share of passing attempts. */
export const fractionTone = (passed: number, n: number) =>
  n === 0 ? "bg-muted-foreground" : passed === n ? "bg-pass" : passed === 0 ? "bg-fail" : "bg-warn";

export function Bar({ value, total, className }: { value: number; total: number; className?: string }) {
  return (
    <div className={cn("h-1.5 overflow-hidden rounded-full bg-muted", className)}>
      <div className="h-full rounded-full bg-info transition-all" style={{ width: `${total ? (100 * value) / total : 0}%` }} />
    </div>
  );
}

export function HealthStrip() {
  const { data, refresh } = usePoll<Health>(api.health, 3000);
  const [busy, setBusy] = useState(false);
  if (!data) return null;
  const s = data.stack;
  const tone = s.state === "ready" ? "pass" : s.state === "starting" ? "info" : s.state === "failed" ? "fail" : "outline";
  const stop = async () => {
    setBusy(true);
    try {
      await api.stopStack();
    } catch (e) {
      alert((e as Error).message);
    }
    setBusy(false);
    refresh();
  };
  return (
    <div className="flex items-center gap-2 text-xs">
      <Badge tone={tone} title={s.error ?? `since ${ago(s.since)}`}>
        {s.state === "starting" && <Loader2 className="size-3 animate-spin" />}
        Gym stack: {s.state}
        {s.config ? ` · ${s.config}` : ""}
      </Badge>
      {(s.state === "ready" || s.state === "starting" || s.state === "failed") && (
        <Button size="xs" variant="outline" onClick={stop} disabled={busy} title="Stop the Gym servers and Ray">
          <Power /> Stop
        </Button>
      )}
    </div>
  );
}
