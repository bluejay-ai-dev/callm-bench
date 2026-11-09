import { useEffect, useMemo, useState } from "react";
import { Bot, FlaskConical, Play } from "lucide-react";
import { api, type ConfigInfo, type TaskRow } from "@/api";
import { Badge, Button, Card, CardHeader, Input, Select } from "@/components/ui/primitives";
import { cn, go } from "@/lib/utils";

const INDUSTRIES = ["healthcare", "legal", "customer-support"];
const key = (t: { industry: string; case_key: string }) => `${t.industry}/${t.case_key}`;

export function NewRunPage() {
  const [configs, setConfigs] = useState<ConfigInfo[]>([]);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [presets, setPresets] = useState<Record<string, { industry: string; case_key: string }[]>>({});
  const [kind, setKind] = useState<"gym" | "oracle">("gym");
  const [config, setConfig] = useState("gpt52");
  const [concurrency, setConcurrency] = useState(32);
  const [repeats, setRepeats] = useState(1);
  const [label, setLabel] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState({ industry: "", category: "", difficulty: "", tag: "", q: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.configs().then(setConfigs, (e) => setError(e.message));
    api.tasks().then((d) => {
      setTasks(d.tasks);
      setPresets(d.presets);
      setSelected(new Set(d.presets.example?.map(key) ?? []));
    }, (e) => setError(e.message));
  }, []);

  const publicTasks = useMemo(() => tasks.filter((t) => t.split === "public"), [tasks]);
  const privateTasks = useMemo(() => tasks.filter((t) => t.split === "private"), [tasks]);

  const visible = useMemo(
    () =>
      tasks.filter(
        (t) =>
          (!filter.industry || t.industry === filter.industry) &&
          (!filter.category || t.category === filter.category) &&
          (!filter.difficulty || t.difficulty === filter.difficulty) &&
          (!filter.tag || (t.tags ?? []).includes(filter.tag)) &&
          (!filter.q || `${t.case_key} ${t.tag} ${t.name}`.toLowerCase().includes(filter.q.toLowerCase())),
      ),
    [tasks, filter],
  );
  const categories = [...new Set(tasks.map((t) => t.category).filter(Boolean))].sort() as string[];
  const difficulties = [...new Set(tasks.map((t) => t.difficulty).filter(Boolean))] as string[];
  const cfg = configs.find((c) => c.name === config);

  const setMany = (keys: string[], on: boolean) =>
    setSelected((s) => {
      const n = new Set(s);
      keys.forEach((k) => (on ? n.add(k) : n.delete(k)));
      return n;
    });

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const picked = tasks.filter((t) => selected.has(key(t))).map((t) => ({ industry: t.industry, case_key: t.case_key }));
      const run = await api.createRun({ kind, tasks: picked, config: kind === "gym" ? config : null, concurrency, repeats, label });
      go(`#/run/${run.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <h1 className="text-xl font-semibold">New run</h1>

      <div className="grid gap-3 md:grid-cols-2">
        <KindCard active={kind === "gym"} onClick={() => setKind("gym")} icon={<Bot />} title="Model run (NeMo Gym)"
          text="A model plays the front desk against the caller simulator; every call is graded. Starts the Gym servers if needed." />
        <KindCard active={kind === "oracle"} onClick={() => setKind("oracle")} icon={<FlaskConical />} title="Oracle replay"
          text="No model, no caller: replays each task's answer key and grades it. Checks that tasks are consistent. Seconds, free." />
      </div>

      {kind === "gym" && (
        <Card>
          <CardHeader title="Models" />
          <div className="grid gap-4 p-4 md:grid-cols-[1fr_auto]">
            <div className="space-y-2">
              <Select value={config} onChange={(e) => setConfig(e.target.value)} className="w-full">
                {configs.map((c) => (
                  <option key={c.name} value={c.name}>
                    configs/{c.name}.yaml
                  </option>
                ))}
              </Select>
              {cfg && (
                <div className="grid grid-cols-[110px_1fr] gap-y-1 text-xs">
                  <span className="text-muted-foreground">model under test</span>
                  <span className="font-mono">{cfg.policy.model}</span>
                  <span className="text-muted-foreground">caller simulator</span>
                  <span className="font-mono">{cfg.user.model}</span>
                  <span className="text-muted-foreground">needs</span>
                  <span className="font-mono">{cfg.keys.join(", ")}</span>
                </div>
              )}
            </div>
            <div className="flex gap-3">
              <label className="space-y-1 text-xs">
                <div className="text-muted-foreground" title="Each task is run k times; results show pass@k and pass^k">Attempts per task (k)</div>
                <Input type="number" min={1} max={20} value={repeats} onChange={(e) => setRepeats(Math.min(20, +e.target.value || 1))} className="w-28" />
              </label>
              <label className="space-y-1 text-xs">
                <div className="text-muted-foreground">Rollouts in parallel</div>
                <Input type="number" min={1} max={256} value={concurrency} onChange={(e) => setConcurrency(+e.target.value || 1)} className="w-28" />
              </label>
            </div>
          </div>
        </Card>
      )}

      <Card>
        <CardHeader title="Tasks">
          <Badge tone="info">{selected.size} selected</Badge>
        </CardHeader>
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <span className="text-xs text-muted-foreground">Quick pick:</span>
          <Button size="xs" variant="outline" onClick={() => setSelected(new Set(publicTasks.map(key)))}>Public {publicTasks.length}</Button>
          <Button size="xs" variant="outline" onClick={() => setSelected(new Set(privateTasks.map(key)))}>Private {privateTasks.length}</Button>
          {INDUSTRIES.map((i) => (
            <Button key={i} size="xs" variant="outline" onClick={() => setSelected(new Set(publicTasks.filter((t) => t.industry === i).map(key)))}>
              {i}
            </Button>
          ))}
          {presets.example && (
            <Button size="xs" variant="outline" onClick={() => setSelected(new Set(presets.example.map(key)))}>
              example (5)
            </Button>
          )}
          <Button size="xs" variant="ghost" onClick={() => setSelected(new Set())}>Clear</Button>
        </div>
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <Select value={filter.industry} onChange={(e) => setFilter({ ...filter, industry: e.target.value })}>
            <option value="">all industries</option>
            {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
          </Select>
          <Select value={filter.category} onChange={(e) => setFilter({ ...filter, category: e.target.value })}>
            <option value="">all categories</option>
            {categories.map((c) => <option key={c}>{c}</option>)}
          </Select>
          <Select value={filter.difficulty} onChange={(e) => setFilter({ ...filter, difficulty: e.target.value })}>
            <option value="">all difficulties</option>
            {difficulties.map((d) => <option key={d}>{d}</option>)}
          </Select>
          <Select value={filter.tag} onChange={(e) => setFilter({ ...filter, tag: e.target.value })}>
            <option value="">all tags</option>
            {[...new Set(tasks.flatMap((t) => t.tags ?? []))].sort().map((g) => <option key={g}>{g}</option>)}
          </Select>
          <Input placeholder="search" value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} className="w-40" />
          <span className="ml-auto flex gap-1">
            <Button size="xs" variant="outline" onClick={() => setMany(visible.map(key), true)}>Select shown ({visible.length})</Button>
            <Button size="xs" variant="ghost" onClick={() => setMany(visible.map(key), false)}>Unselect shown</Button>
          </span>
        </div>
        <div className="grid max-h-80 grid-cols-2 gap-x-4 overflow-auto p-3 md:grid-cols-3">
          {visible.map((t) => (
            <label key={key(t)} className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-accent">
              <input type="checkbox" checked={selected.has(key(t))} onChange={(e) => setMany([key(t)], e.target.checked)} />
              <span className="w-24 shrink-0 text-muted-foreground">{t.industry}</span>
              <span className="shrink-0 font-mono font-medium whitespace-nowrap">{t.tag}</span>
              <span className="truncate">{t.name}</span>
              <span className="ml-auto shrink-0 font-mono text-[10px] text-muted-foreground">{t.case_key}</span>
            </label>
          ))}
        </div>
      </Card>

      <div className="flex items-center gap-2">
        <Input placeholder="Label (optional)" value={label} onChange={(e) => setLabel(e.target.value)} className="w-72" />
        {error && <span className="text-sm text-fail">{error}</span>}
        <Button className="ml-auto" onClick={submit} disabled={busy || selected.size === 0}>
          <Play /> Start {kind === "oracle" ? "oracle replay" : "run"} on {selected.size} task{selected.size === 1 ? "" : "s"}
          {kind === "gym" && repeats > 1 ? ` × ${repeats} = ${selected.size * repeats} rollouts` : ""}
        </Button>
      </div>
    </div>
  );
}

function KindCard({ active, onClick, icon, title, text }: { active: boolean; onClick: () => void; icon: React.ReactNode; title: string; text: string }) {
  return (
    <button onClick={onClick} className={cn("rounded-lg border bg-card p-4 text-left transition-colors [&_svg]:size-5", active ? "border-info ring-2 ring-info/30" : "hover:bg-accent/50")}>
      <div className="flex items-center gap-2 font-medium">
        {icon} {title}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{text}</p>
    </button>
  );
}
