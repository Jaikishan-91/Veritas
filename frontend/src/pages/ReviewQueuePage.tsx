import { useEffect, useState } from "react";
import { api, type DocumentSummary } from "../api";
import { DocTable } from "../components/RiskBadge";

type Tab = "pending" | "reviewed";

export default function ReviewQueuePage() {
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [tab, setTab] = useState<Tab>("pending");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.reviews(true).then(setDocs).catch((e) => setError(e.message)); }, []);

  const pending = docs?.filter((d) => !d.reviewed) ?? [];
  const reviewed = docs?.filter((d) => d.reviewed) ?? [];
  const tabBtn = (t: Tab, label: string, n: number) => (
    <button onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${tab === t ? "bg-brand text-brand-fg" : "text-muted hover:bg-surface-2 hover:text-fg"}`}>
      {label} <span className="tabular-nums opacity-70">({n})</span>
    </button>
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Review queue</h1>
        <p className="mt-1 text-sm text-muted">
          Documents routed for human review: uncertain risk score, reduced detector coverage, or analysis failure.
          Owners are notified of each decision.
        </p>
      </div>
      <div className="flex gap-1">{tabBtn("pending", "Pending", pending.length)}{tabBtn("reviewed", "Reviewed", reviewed.length)}</div>
      {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">{error}</p>}
      {docs
        ? <DocTable docs={tab === "pending" ? pending : reviewed}
                    empty={tab === "pending" ? "Nothing waiting for review." : "No reviewed documents yet."} />
        : <p className="text-sm text-muted">Loading…</p>}
    </div>
  );
}
