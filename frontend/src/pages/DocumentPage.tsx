import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth";
import { api, type Decision, type DocumentDetail, type Finding } from "../api";
import { CAT_COLOR, PageView, usePdf } from "../components/PageView";
import { DecisionBadge, RiskBadge } from "../components/RiskBadge";

const pct = (x: number) => `${Math.round(x * 100)}%`;

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [active, setActive] = useState<number | null>(null);
  const [heat, setHeat] = useState<string>("none");
  const [heatOpacity, setHeatOpacity] = useState(0.6);
  const viewerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(700);
  const { user } = useAuth();
  const canReview = user?.role === "reviewer" || user?.role === "admin";

  useEffect(() => {
    let timer: number | undefined;
    const load = () =>
      api.get(id!).then((d) => {
        setDoc(d);
        if (d.status === "queued" || d.status === "processing") timer = window.setTimeout(load, 1500);
      }).catch((e) => setError(e.message));
    load();
    return () => window.clearTimeout(timer);
  }, [id]);

  useEffect(() => {
    const el = viewerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.min(900, Math.floor(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [doc?.id]);

  const pdf = usePdf(doc?.kind === "pdf" ? doc.file_url : null);
  const pages = doc?.page_sizes.length || 1;
  const heatKinds = useMemo(() => [...new Set(doc?.artifacts.map((a) => a.kind) ?? [])], [doc]);
  const heatUrl = doc?.artifacts.find((a) => a.kind === heat && a.page === page)?.url ?? null;

  if (error) return <p className="rounded-lg bg-rose-100 p-3 text-sm text-rose-800 dark:bg-rose-500/15 dark:text-rose-300">{error}</p>;
  if (!doc) return <p className="text-muted">Loading…</p>;

  const select = (f: Finding) => { setActive(f.id); if (f.page != null) setPage(f.page); };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
      <section className="space-y-3 min-w-0">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <h1 className="text-lg font-semibold tracking-tight truncate max-w-md" title={doc.filename}>{doc.filename}</h1>
          <RiskBadge doc={doc} />
          {pages > 1 && (
            <div className="flex items-center gap-1">
              <button className="btn btn-ghost px-2 disabled:opacity-40" disabled={page === 0} onClick={() => setPage(page - 1)}>‹</button>
              <span className="tabular-nums text-muted">Page {page + 1} / {pages}</span>
              <button className="btn btn-ghost px-2 disabled:opacity-40" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>›</button>
            </div>
          )}
          {heatKinds.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-muted">Heatmap</span>
              <div className="inline-flex flex-wrap gap-1 rounded-lg border border-line bg-surface p-1" role="group" aria-label="Heatmap">
                {["none", ...heatKinds].map((k) => (
                  <button key={k} type="button" onClick={() => setHeat(k)} aria-pressed={heat === k}
                          className={`btn btn-ghost px-2 py-0.5 text-xs ${heat === k ? "bg-brand-soft text-brand" : ""}`}>
                    {k === "none" ? "none" : k.replace("_heatmap", "")}
                  </button>
                ))}
              </div>
              {heat !== "none" && (
                <input type="range" min={0.1} max={1} step={0.05} value={heatOpacity} onChange={(e) => setHeatOpacity(+e.target.value)} />
              )}
            </div>
          )}
        </div>
        <div ref={viewerRef} className="w-full">
          <PageView kind={doc.kind} fileUrl={doc.file_url} pdf={pdf} page={page} width={width}
                    findings={doc.findings} heatmapUrl={heat === "none" ? null : heatUrl} heatOpacity={heatOpacity}
                    activeId={active} onSelect={(fid) => setActive(fid)} />
        </div>
      </section>

      <aside className="space-y-4">
        <Summary doc={doc} />
        <DecisionBanner doc={doc} />
        {doc.needs_review && canReview && <ReviewForm doc={doc} onDone={setDoc} />}
        <section>
          <h2 className="font-semibold mb-2 text-sm uppercase tracking-wide text-muted">Evidence ({doc.findings.length})</h2>
          {doc.status === "completed" && doc.findings.length === 0 && (
            <p className="text-sm text-muted">No suspicious signals found by the detectors that ran.</p>
          )}
          <ol className="space-y-2">
            {doc.findings.map((f) => (
              <li key={f.id}>
                <button onClick={() => select(f)}
                        className={`w-full text-left rounded-lg border p-3 text-sm transition-colors hover:bg-brand-soft ${f.id === active ? "border-brand bg-brand-soft ring-1 ring-brand" : "border-line bg-surface"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2 rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium">
                      <span className="inline-block size-2.5 rounded-full" style={{ background: CAT_COLOR[f.category] }} />
                      {f.category.replace("_", " ")}
                    </span>
                    <span className="text-xs text-muted tabular-nums">
                      +{f.contribution.toFixed(2)} · sev {pct(f.severity)} · conf {pct(f.confidence)}
                    </span>
                  </div>
                  <p className="mt-1.5 text-fg">{f.description}</p>
                  <div className="mt-2 h-1 rounded-full bg-surface-2 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${Math.min(100, Math.round(f.contribution * 100))}%`, background: CAT_COLOR[f.category] }} />
                  </div>
                  <p className="mt-1 text-xs text-muted">{f.detector}{f.page != null ? ` · page ${f.page + 1}` : ""}{f.bbox ? "" : " · no location"}</p>
                  {f.id === active && (
                    <pre className="mt-2 max-h-48 overflow-auto rounded bg-surface-2 p-2 text-xs text-muted whitespace-pre-wrap">
                      {JSON.stringify(f.evidence, null, 2)}
                    </pre>
                  )}
                </button>
              </li>
            ))}
          </ol>
        </section>
        <details className="card text-sm overflow-hidden">
          <summary className="cursor-pointer bg-surface-2 px-3 py-2 font-semibold">Detector runs</summary>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-muted">
                <th className="px-3 py-1.5 font-medium">Detector</th>
                <th className="py-1.5 font-medium">Status</th>
                <th className="py-1.5 text-right font-medium">Findings</th>
                <th className="px-3 py-1.5 text-right font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {doc.detector_runs.map((r) => (
                <tr key={r.detector} className="border-t border-line">
                  <td className="px-3 py-1.5">{r.detector}</td>
                  <td className={r.status === "ok" ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"} title={r.error}>{r.status}</td>
                  <td className="text-right tabular-nums">{r.findings ?? "–"}</td>
                  <td className="px-3 text-right tabular-nums text-muted">{r.ms} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </aside>
    </div>
  );
}

function Summary({ doc }: { doc: DocumentDetail }) {
  if (doc.status === "queued" || doc.status === "processing")
    return <div className="card p-4 text-sm text-muted animate-pulse">Analysing… ({doc.status})</div>;
  if (doc.status === "failed")
    return <div className="rounded-lg border border-rose-200 bg-rose-100 p-4 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/15 dark:text-rose-300">Analysis failed: {doc.error}</div>;
  const s = doc.risk_score ?? 0;
  const color = doc.risk_band === "high" ? "#e11d48" : doc.risk_band === "medium" ? "#d97706" : "#059669";
  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted">Risk score</div>
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-semibold tabular-nums tracking-tight" style={{ color }}>{s.toFixed(2)}</span>
            <span className="text-sm font-medium uppercase tracking-wide" style={{ color }}>{doc.risk_band}</span>
          </div>
        </div>
        <div className="text-right text-xs text-muted">
          coverage {pct(doc.coverage ?? 0)}<br />{doc.page_count} page(s) · {doc.kind.toUpperCase()}
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: pct(s), background: color }} />
      </div>
      <p className="text-xs text-muted">
        Probabilistic indicator from heuristic detectors, not a verdict. Scores are uncalibrated.
      </p>
      {doc.needs_review && (
        <div className="rounded-lg border border-line bg-brand-soft p-2.5 text-xs text-brand">
          Routed to human review: {doc.review_reasons.join("; ")}
        </div>
      )}
    </div>
  );
}

const DECISIONS: [Decision, string][] = [["accepted", "Accept"], ["rejected", "Reject"], ["inconclusive", "Inconclusive"]];

function DecisionBanner({ doc }: { doc: DocumentDetail }) {
  const last = doc.reviews.at(-1);
  if (!last) return null;
  const tone = last.decision === "accepted" ? "border-emerald-200 bg-emerald-100 dark:border-emerald-500/30 dark:bg-emerald-500/15"
    : last.decision === "rejected" ? "border-rose-200 bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/15" : "border-line bg-surface-2";
  return (
    <div className={`rounded-lg border p-4 text-sm space-y-1 ${tone}`}>
      <div className="flex items-center gap-2 font-semibold">Review decision <DecisionBadge decision={last.decision as Decision} /></div>
      {last.notes && <p className="text-fg">{last.notes}</p>}
      <p className="text-xs text-muted">by {last.reviewer} · {new Date(last.created_at).toLocaleString()}</p>
    </div>
  );
}

function ReviewForm({ doc, onDone }: { doc: DocumentDetail; onDone: (d: DocumentDetail) => void }) {
  const [decision, setDecision] = useState<Decision>("inconclusive");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const last = doc.reviews.at(-1);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api.review(doc.id, { decision, notes });
      onDone(await api.get(doc.id));
      setNotes("");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={submit} className="card p-4 space-y-3 text-sm">
      <h2 className="font-semibold">Human review</h2>
      {last && <p className="text-xs text-muted">Last decision: <b>{last.decision}</b>{last.reviewer && ` by ${last.reviewer}`} — {last.notes}</p>}
      <div className="flex gap-2">
        {DECISIONS.map(([d, label]) => (
          <label key={d} className={`flex-1 cursor-pointer rounded-lg border px-2 py-1 text-center transition-colors ${decision === d ? "border-brand bg-brand-soft text-brand font-medium" : "border-line text-muted hover:bg-surface-2"}`}>
            <input type="radio" className="hidden" name="decision" value={d} checked={decision === d} onChange={() => setDecision(d)} />{label}
          </label>
        ))}
      </div>
      <textarea className="input w-full" rows={3} placeholder="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={5000} />
      {err && <p className="text-rose-700 dark:text-rose-300 text-xs">{err}</p>}
      <button disabled={busy} className="btn btn-primary disabled:opacity-50">Submit review</button>
    </form>
  );
}
