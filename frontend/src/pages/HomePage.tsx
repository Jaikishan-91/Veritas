import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DocumentSummary } from "../api";
import { useAuth } from "../auth";
import { DocTable } from "../components/RiskBadge";

function Stat({ label, value, tone = "text-fg" }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-3xl font-semibold tabular-nums ${tone}`}>{value}</div>
    </div>
  );
}

export default function HomePage() {
  const { user } = useAuth();
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [queue, setQueue] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reviewer = user?.role === "admin" || (user?.role === "organisation" && user.approved);

  useEffect(() => {
    api.list().then(setDocs).catch((e) => setError(e.message));
    if (reviewer) api.reviews().then((q) => setQueue(q.length)).catch(() => {});
  }, [reviewer]);

  const count = (band: string) => docs?.filter((d) => d.risk_band === band).length ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1 text-sm text-muted">{user?.username ?? user?.email}</p>
        </div>
        <Link to="/analyze" className="btn btn-primary">Analyze a document</Link>
      </div>
      {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">{error}</p>}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
        <Stat label="Your documents" value={docs?.length ?? "–"} />
        <Stat label="High risk" value={count("high")} tone="text-rose-600 dark:text-rose-400" />
        <Stat label="Medium risk" value={count("medium")} tone="text-amber-600 dark:text-amber-400" />
        <Stat label="Low risk" value={count("low")} tone="text-emerald-600 dark:text-emerald-400" />
        {reviewer
          ? <Link to="/reviews"><Stat label="Awaiting review" value={queue ?? "–"} tone="text-brand" /></Link>
          : <Stat label="Flagged for review" value={docs?.filter((d) => d.needs_review && !d.reviewed).length ?? 0} tone="text-brand" />}
      </div>
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Recent documents</h2>
          <Link to="/analyze" className="text-sm font-medium text-brand hover:underline">View all</Link>
        </div>
        {docs ? <DocTable docs={docs.slice(0, 5)} empty="You haven't analysed any documents yet." /> : <p className="text-sm text-muted">Loading…</p>}
      </section>
    </div>
  );
}
