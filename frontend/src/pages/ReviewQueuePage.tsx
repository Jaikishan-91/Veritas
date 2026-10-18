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
            className={`rounded-md px-3 py-1.5 text-sm ${tab === t ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"}`}>
      {label} <span className="tabular-nums opacity-70">({n})</span>
    </button>
  );

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Review queue</h1>
      <p className="text-sm text-slate-600">
        Documents routed for human review: uncertain risk score, reduced detector coverage, or analysis failure.
        Owners are notified of each decision.
      </p>
      <div className="flex gap-1">{tabBtn("pending", "Pending", pending.length)}{tabBtn("reviewed", "Reviewed", reviewed.length)}</div>
      {error && <p className="rounded bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      {docs
        ? <DocTable docs={tab === "pending" ? pending : reviewed}
                    empty={tab === "pending" ? "Nothing waiting for review." : "No reviewed documents yet."} />
        : <p className="text-sm text-slate-500">Loading…</p>}
    </div>
  );
}
