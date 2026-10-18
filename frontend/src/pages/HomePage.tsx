import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DocumentSummary } from "../api";
import { useAuth } from "../auth";
import { DocTable } from "../components/RiskBadge";

function Stat({ label, value, tone = "text-slate-900" }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="rounded-xl border bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-3xl font-semibold tabular-nums ${tone}`}>{value}</div>
    </div>
  );
}

export default function HomePage() {
  const { user } = useAuth();
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [queue, setQueue] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reviewer = user?.role === "reviewer" || user?.role === "admin";

  useEffect(() => {
    api.list().then(setDocs).catch((e) => setError(e.message));
    if (reviewer) api.reviews().then((q) => setQueue(q.length)).catch(() => {});
  }, [reviewer]);

  const count = (band: string) => docs?.filter((d) => d.risk_band === band).length ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Welcome back</h1>
          <p className="text-sm text-slate-500">{user?.email}</p>
        </div>
        <Link to="/analyze" className="rounded-lg bg-slate-900 px-4 py-2 text-white">Analyze a document</Link>
      </div>
      {error && <p className="rounded bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
        <Stat label="Your documents" value={docs?.length ?? "–"} />
        <Stat label="High risk" value={count("high")} tone="text-rose-600" />
        <Stat label="Medium risk" value={count("medium")} tone="text-amber-600" />
        <Stat label="Low risk" value={count("low")} tone="text-emerald-600" />
        {reviewer
          ? <Link to="/reviews"><Stat label="Awaiting review" value={queue ?? "–"} tone="text-blue-700" /></Link>
          : <Stat label="Flagged for review" value={docs?.filter((d) => d.needs_review && !d.reviewed).length ?? 0} tone="text-blue-700" />}
      </div>
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Recent documents</h2>
          <Link to="/analyze" className="text-sm text-blue-700 hover:underline">View all</Link>
        </div>
        {docs ? <DocTable docs={docs.slice(0, 5)} empty="You haven't analysed any documents yet." /> : <p className="text-sm text-slate-500">Loading…</p>}
      </section>
    </div>
  );
}
