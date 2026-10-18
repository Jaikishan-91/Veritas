import { Link } from "react-router-dom";
import type { DocumentSummary } from "../api";

const BAND: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-rose-100 text-rose-800",
};

export function RiskBadge({ doc }: { doc: Pick<DocumentSummary, "status" | "risk_score" | "risk_band"> }) {
  if (doc.status !== "completed" || doc.risk_score == null)
    return <span className="rounded px-2 py-0.5 text-xs bg-slate-100 text-slate-600">{doc.status}</span>;
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium tabular-nums ${BAND[doc.risk_band ?? "low"]}`}>
      {doc.risk_score.toFixed(2)} · {doc.risk_band}
    </span>
  );
}

export function DocTable({ docs, empty }: { docs: DocumentSummary[]; empty: string }) {
  if (!docs.length) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <table className="w-full text-sm bg-white border rounded-lg overflow-hidden">
      <thead className="bg-slate-100 text-left text-slate-600">
        <tr><th className="p-2">File</th><th className="p-2">Type</th><th className="p-2">Risk</th><th className="p-2">Review</th><th className="p-2">Uploaded</th></tr>
      </thead>
      <tbody>
        {docs.map((d) => (
          <tr key={d.id} className="border-t hover:bg-slate-50">
            <td className="p-2"><Link className="text-blue-700 hover:underline" to={`/documents/${d.id}`}>{d.filename}</Link></td>
            <td className="p-2 uppercase text-slate-500">{d.kind}</td>
            <td className="p-2"><RiskBadge doc={d} /></td>
            <td className="p-2 text-slate-600">{d.reviewed ? "reviewed" : d.needs_review ? "pending" : "—"}</td>
            <td className="p-2 text-slate-500">{new Date(d.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
