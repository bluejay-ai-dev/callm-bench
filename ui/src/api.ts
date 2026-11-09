// Typed client for the `micol ui` backend (src/micol/console/api.py).

export type RunStatus = "queued" | "starting" | "running" | "done" | "failed" | "cancelled" | "interrupted";

export interface Block {
  n: number;
  passed: number;
  tools: number;
  handoffs: number;
  db: number;
  shaped: number | null;
  errors: number;
  tasks: number;
  k: number;
  pass_any: number; // pass@k: tasks with at least one passing attempt
  pass_all: number; // pass^k: tasks whose every attempt passed
}

export interface Summary {
  all: Block;
  by_industry: Record<string, Block>;
}

export interface RunMeta {
  id: string;
  label: string;
  kind: "gym" | "oracle";
  config: string | null;
  caller?: string | null;
  source?: Record<string, unknown> | null;
  concurrency: number;
  repeats?: number;
  total: number;
  status: RunStatus;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  done: number;
  summary: Summary;
}

export interface RowBrief {
  industry: string;
  case_key: string;
  tag: string;
  title: string;
  attempt: number;
  category: string | null;
  difficulty: string | null;
  passed: boolean;
  shaped: number | null;
  tools: boolean;
  handoffs: boolean;
  db: boolean;
  ended_by: string | null;
  failure_kind: string | null;
  turns: number;
  tool_calls: number;
}

export interface RunDetail extends RunMeta {
  rows: RowBrief[];
}

export interface TaskRow {
  industry: string;
  case_key: string;
  name: string;
  category: string | null;
  difficulty: string | null;
  calls: number;
  handoffs: number;
  tag: string;
  split: string | null;
  tags: string[];
}

export interface ToolCall {
  name: string;
  parameters?: Record<string, unknown> | null;
  oracle_parameters?: Record<string, unknown>;
  output?: Record<string, unknown>;
}

export interface Task {
  task_id: string;
  task_name: string;
  intent: string;
  traits: { trait_name: string; value: string }[];
  scripted_responses?: { match_phrase?: string; response_value?: string }[];
  behaviors?: Record<string, unknown>;
  exp_handoff_path: string[];
  exp_tool_calls: ToolCall[];
  exp_db_state?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export type TimelineEvent =
  | { kind: "message"; role: "agent" | "customer"; text: string; said?: string; dropped?: boolean }
  | {
      kind: "tool";
      index: number;
      name: string;
      parameters: Record<string, unknown> | null;
      agent: string | null;
      ok: boolean | null;
      error_code: string | null;
      result: unknown;
    }
  | { kind: "handoff"; agent: string };

export type ArgStatus = "match" | "differs" | "missing" | "default" | "prose" | "empty" | "ignored" | "unchecked";
export type ToolRowStatus = "match" | "params_differ" | "output_differs" | "params_and_output_differ" | "missing" | "extra" | "forbidden";

export interface ToolRow {
  status: ToolRowStatus;
  name: string;
  actual_index: number | null;
  expected_index: number | null;
  agent: string | null;
  args: { key: string; expected: unknown; actual: unknown; present: boolean; status: ArgStatus }[];
  outcome: {
    expected: { ok?: boolean; error_code?: string } | null;
    actual: { ok?: boolean; error_code?: string } | null;
    match: boolean;
  };
  reply: unknown;
}

export interface Grading {
  tool_rows: ToolRow[];
  expected_count: number;
  actual_count: number;
  handoffs: { expected: string[]; actual: string[] };
  db_tables: { table: string; expected: unknown; actual: unknown; same: boolean }[];
  components: Record<string, { passed: boolean; [k: string]: unknown }>;
  scores: Record<string, number | null>;
}

export interface Rollout {
  industry: string;
  case_key: string;
  conjunctive: number;
  shaped: number;
  ended_by: string | null;
  failure_kind: string | null;
  failure_reason: string | null;
  system_prompt_swaps: { after_tool_call: number; agent: string; system_prompt: string }[];
  final_state: Record<string, unknown>;
  trace: { name: string; parameters: Record<string, unknown>; agent: string; ok: boolean; error_code?: string }[];
}

export interface RolloutView {
  rollout: Rollout;
  timeline: TimelineEvent[];
  grading: Grading;
  task?: Task;
  tag?: string;
  attempt?: number;
  attempts?: RowBrief[];
}

export interface Health {
  stack: { state: "stopped" | "starting" | "ready" | "failed"; config: string | null; since: string; error: string | null };
  queue: { current: string | null; pending: string[] };
}

export interface ConfigInfo {
  name: string;
  description: string;
  policy: { model: string | null; base_url: string | null };
  user: { model: string | null; base_url: string | null };
  keys: string[];
}

export interface TaskDetail {
  task: Task;
  tag: string;
  agents: { name: string; tools: string[] }[];
  start: string;
  history: { run: { id: string; label: string; kind: string; config: string | null; created_at: string }; attempts: RowBrief[] }[];
}

export interface CompareView {
  runs: RunMeta[];
  tasks: { key: string; industry: string; case_key: string; tag: string; title: string; cells: Record<string, RowBrief[]> }[];
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

const enc = encodeURIComponent;

export const api = {
  health: () => call<Health>("/health"),
  stopStack: () => call<Health["stack"]>("/stack/stop", { method: "POST" }),
  stackLog: () => call<{ log: string }>("/stack/log?lines=200"),
  configs: () => call<ConfigInfo[]>("/configs"),
  tasks: () => call<{ tasks: TaskRow[]; presets: Record<string, { industry: string; case_key: string }[]> }>("/tasks"),
  task: (industry: string, key: string) => call<TaskDetail>(`/tasks/${enc(industry)}/${enc(key)}`),
  oracle: (industry: string, key: string) =>
    call<RolloutView>(`/tasks/${enc(industry)}/${enc(key)}/oracle`, { method: "POST" }),
  runs: () => call<RunMeta[]>("/runs"),
  run: (id: string) => call<RunDetail>(`/runs/${enc(id)}`),
  runLog: (id: string) => call<{ log: string }>(`/runs/${enc(id)}/log?lines=300`),
  createRun: (body: {
    kind: "gym" | "oracle";
    tasks: { industry: string; case_key: string }[];
    config?: string | null;
    concurrency: number;
    repeats: number;
    label: string;
  }) => call<RunMeta>("/runs", { method: "POST", body: JSON.stringify(body) }),
  cancel: (id: string) => call<RunMeta>(`/runs/${enc(id)}/cancel`, { method: "POST" }),
  rerun: (id: string) => call<RunMeta>(`/runs/${enc(id)}/rerun`, { method: "POST" }),
  remove: (id: string) => call<{ deleted: boolean }>(`/runs/${enc(id)}`, { method: "DELETE" }),
  rollout: (id: string, industry: string, key: string, attempt: number) =>
    call<RolloutView>(`/runs/${enc(id)}/rollouts/${enc(industry)}/${enc(key)}/${attempt}`),
  compare: (ids: string[]) => call<CompareView>(`/compare?ids=${ids.map(enc).join(",")}`),
};

/** A task's attempts within one run. */
export interface TaskGroup {
  industry: string;
  case_key: string;
  tag: string;
  title: string;
  difficulty: string | null;
  attempts: RowBrief[];
  passed: number;
}

export function groupByTask(rows: RowBrief[]): TaskGroup[] {
  const m = new Map<string, TaskGroup>();
  for (const r of rows) {
    const k = `${r.industry}/${r.case_key}`;
    const g = m.get(k) ?? { industry: r.industry, case_key: r.case_key, tag: r.tag, title: r.title, difficulty: r.difficulty, attempts: [], passed: 0 };
    g.attempts.push(r);
    if (r.passed) g.passed++;
    m.set(k, g);
  }
  const out = [...m.values()];
  out.forEach((g) => g.attempts.sort((a, b) => a.attempt - b.attempt));
  return out.sort((a, b) => a.industry.localeCompare(b.industry) || a.tag.localeCompare(b.tag, undefined, { numeric: true }) || a.title.localeCompare(b.title));
}

export const taskHash = (runId: string, industry: string, caseKey: string, attempt = 0) =>
  `#/run/${runId}/${industry}/${caseKey}/${attempt}`;
