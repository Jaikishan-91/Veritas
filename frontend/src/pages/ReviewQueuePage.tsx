import { useEffect, useState } from "react";
import { api, type DocumentSummary } from "../api";
import { DocTable } from "../components/RiskBadge";

export default function ReviewQueuePage() {
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.reviews().then(setDocs).catch((e) => setError(e.message)); }, []);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Review queue</h1>
      <p className="text-sm text-slate-600">
        Documents routed for human review: uncertain risk score, reduced detector coverage, or analysis failure.
      </p>
      {error && <p className="rounded bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      {docs ? <DocTable docs={docs} empty="Nothing waiting for review." /> : <p className="text-sm text-slate-500">Loading…</p>}
    </div>
  );
}
