import { Link } from "react-router-dom";
import type { Decision, DocumentSummary } from "../api";

const PILL = "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium";

const DECISION: Record<Decision, { pill: string; dot: string }> = {
  accepted: { pill: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300", dot: "bg-emerald-500" },
  rejected: { pill: "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-300", dot: "bg-rose-500" },
  inconclusive: { pill: "bg-surface-2 text-muted", dot: "bg-muted" },
};

export function DecisionBadge({ decision }: { decision: Decision }) {
  const s = DECISION[decision];
  return (
    <span className={`${PILL} ${s.pill}`}>
      <span className={`size-1.5 rounded-full ${s.dot}`} />
      {decision}
    </span>
  );
}

const BAND: Record<string, { pill: string; dot: string }> = {
  low: { pill: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300", dot: "bg-emerald-500" },
  medium: { pill: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300", dot: "bg-amber-500" },
  high: { pill: "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-300", dot: "bg-rose-500" },
};

export function RiskBadge({ doc }: { doc: Pick<DocumentSummary, "status" | "risk_score" | "risk_band"> }) {
  if (doc.status !== "completed" || doc.risk_score == null)
    return <span className={`${PILL} bg-surface-2 text-muted`}>{doc.status}</span>;
  const s = BAND[doc.risk_band ?? "low"];
  return (
    <span className={`${PILL} ${s.pill}`}>
      <span className={`size-1.5 rounded-full ${s.dot}`} />
      <span className="tabular-nums">{doc.risk_score.toFixed(2)}</span> · {doc.risk_band}
    </span>
  );
}

export function DocTable({ docs, empty }: { docs: DocumentSummary[]; empty: string }) {
  if (!docs.length) return <p className="text-sm text-muted">{empty}</p>;
  const th = "px-4 py-3 font-medium";
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-surface-2 text-left text-xs uppercase tracking-wide text-muted">
            <tr><th className={th}>File</th><th className={th}>Type</th><th className={th}>Organisation</th><th className={th}>Risk</th><th className={th}>Review</th><th className={th}>Uploaded</th></tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className="border-t border-line hover:bg-surface-2">
                <td className="px-4 py-3"><Link className="font-medium text-fg hover:text-brand" to={`/documents/${d.id}`}>{d.filename}</Link></td>
                <td className="px-4 py-3 text-xs uppercase text-muted">{d.kind}</td>
                <td className="px-4 py-3 text-muted">{d.organisation ?? "—"}</td>
                <td className="px-4 py-3"><RiskBadge doc={d} /></td>
                <td className="px-4 py-3 text-muted">{d.decision ? <DecisionBadge decision={d.decision} /> : d.needs_review ? "pending" : "—"}</td>
                <td className="px-4 py-3 text-muted">{new Date(d.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
