import { useEffect, useState } from "react";
import { ListChecks, Play, Plus } from "lucide-react";
import { HealthStrip } from "@/components/shared";
import { Button } from "@/components/ui/primitives";
import { ComparePage } from "@/pages/ComparePage";
import { NewRunPage } from "@/pages/NewRunPage";
import { RolloutPage } from "@/pages/RolloutPage";
import { RunPage } from "@/pages/RunPage";
import { RunsPage } from "@/pages/RunsPage";
import { TaskPage, TasksPage } from "@/pages/TasksPage";
import { cn, go } from "@/lib/utils";

// The hash is the whole router, so every run, rollout, and task is linkable and survives a refresh.
type Route =
  | { page: "runs" }
  | { page: "new" }
  | { page: "run"; id: string }
  | { page: "rollout"; id: string; industry: string; caseKey: string; attempt: number }
  | { page: "tasks" }
  | { page: "task"; industry: string; caseKey: string }
  | { page: "compare"; ids: string[] };

function parse(): Route {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  switch (parts[0]) {
    case "new":
      return { page: "new" };
    case "run":
      return parts.length >= 4
        ? { page: "rollout", id: parts[1], industry: parts[2], caseKey: parts[3], attempt: Number(parts[4] ?? 0) || 0 }
        : { page: "run", id: parts[1] };
    case "tasks":
      return { page: "tasks" };
    case "task":
      return { page: "task", industry: parts[1], caseKey: parts[2] };
    case "compare":
      return { page: "compare", ids: (parts[1] ?? "").split(",") };
    default:
      return { page: "runs" };
  }
}

export default function App() {
  const [route, setRoute] = useState<Route>(parse);
  useEffect(() => {
    const on = () => {
      setRoute(parse());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  const section = route.page === "tasks" || route.page === "task" ? "tasks" : route.page === "new" ? "new" : "runs";
  const nav = (key: string, hash: string, icon: React.ReactNode, label: string) => (
    <Button variant="ghost" size="sm" onClick={() => go(hash)} className={cn(section === key && "bg-accent")}>
      {icon} {label}
    </Button>
  );

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-3 px-6">
          <button onClick={() => go("#/")} className="text-sm font-semibold tracking-tight">
            CALLM Console
          </button>
          <nav className="ml-3 flex items-center gap-1">
            {nav("runs", "#/", <Play />, "Runs")}
            {nav("new", "#/new", <Plus />, "New run")}
            {nav("tasks", "#/tasks", <ListChecks />, "Tasks")}
          </nav>
          <div className="ml-auto">
            <HealthStrip />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1600px] px-6 py-6">
        {route.page === "runs" && <RunsPage />}
        {route.page === "new" && <NewRunPage />}
        {route.page === "run" && <RunPage id={route.id} />}
        {route.page === "rollout" && <RolloutPage runId={route.id} industry={route.industry} caseKey={route.caseKey} attempt={route.attempt} />}
        {route.page === "tasks" && <TasksPage />}
        {route.page === "task" && <TaskPage industry={route.industry} caseKey={route.caseKey} />}
        {route.page === "compare" && <ComparePage ids={route.ids} />}
      </main>
    </div>
  );
}
