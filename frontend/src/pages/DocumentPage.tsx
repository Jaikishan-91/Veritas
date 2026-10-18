import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth";
import { api, type DocumentDetail, type Finding } from "../api";
import { CAT_COLOR, PageView, usePdf } from "../components/PageView";
import { RiskBadge } from "../components/RiskBadge";

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

  if (error) return <p className="rounded bg-rose-50 p-3 text-sm text-rose-700">{error}</p>;
  if (!doc) return <p className="text-slate-500">Loading…</p>;

  const select = (f: Finding) => { setActive(f.id); if (f.page != null) setPage(f.page); };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
      <section className="space-y-3 min-w-0">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <h1 className="text-lg font-semibold truncate max-w-md" title={doc.filename}>{doc.filename}</h1>
          <RiskBadge doc={doc} />
          {pages > 1 && (
            <div className="flex items-center gap-1">
              <button className="px-2 border rounded disabled:opacity-40" disabled={page === 0} onClick={() => setPage(page - 1)}>‹</button>
              <span className="tabular-nums">Page {page + 1} / {pages}</span>
              <button className="px-2 border rounded disabled:opacity-40" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>›</button>
            </div>
          )}
          {heatKinds.length > 0 && (
            <label className="flex items-center gap-2">
              Heatmap
              <select className="border rounded px-1 py-0.5" value={heat} onChange={(e) => setHeat(e.target.value)}>
                <option value="none">none</option>
                {heatKinds.map((k) => <option key={k} value={k}>{k.replace("_heatmap", "")}</option>)}
              </select>
              {heat !== "none" && (
                <input type="range" min={0.1} max={1} step={0.05} value={heatOpacity} onChange={(e) => setHeatOpacity(+e.target.value)} />
              )}
            </label>
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
        {doc.needs_review && canReview && <ReviewForm doc={doc} onDone={setDoc} />}
        <section>
          <h2 className="font-semibold mb-2">Evidence ({doc.findings.length})</h2>
          {doc.status === "completed" && doc.findings.length === 0 && (
            <p className="text-sm text-slate-500">No suspicious signals found by the detectors that ran.</p>
          )}
          <ol className="space-y-2">
            {doc.findings.map((f) => (
              <li key={f.id}>
                <button onClick={() => select(f)}
                        className={`w-full text-left rounded-lg border bg-white p-3 text-sm hover:border-slate-400 ${f.id === active ? "border-slate-900 ring-1 ring-slate-900" : ""}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2 font-medium">
                      <span className="inline-block size-2.5 rounded-full" style={{ background: CAT_COLOR[f.category] }} />
                      {f.category.replace("_", " ")}
                    </span>
                    <span className="text-xs text-slate-500 tabular-nums">
                      +{f.contribution.toFixed(2)} · sev {pct(f.severity)} · conf {pct(f.confidence)}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-700">{f.description}</p>
                  <p className="mt-1 text-xs text-slate-400">{f.detector}{f.page != null ? ` · page ${f.page + 1}` : ""}{f.bbox ? "" : " · no location"}</p>
                  {f.id === active && (
                    <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-50 p-2 text-xs text-slate-600 whitespace-pre-wrap">
                      {JSON.stringify(f.evidence, null, 2)}
                    </pre>
                  )}
                </button>
              </li>
            ))}
          </ol>
        </section>
        <details className="text-sm">
          <summary className="cursor-pointer font-semibold">Detector runs</summary>
          <table className="mt-2 w-full text-xs">
            <tbody>
              {doc.detector_runs.map((r) => (
                <tr key={r.detector} className="border-t">
                  <td className="py-1">{r.detector}</td>
                  <td className={r.status === "ok" ? "text-emerald-700" : "text-amber-700"} title={r.error}>{r.status}</td>
                  <td className="text-right tabular-nums">{r.findings ?? "–"}</td>
                  <td className="text-right tabular-nums text-slate-500">{r.ms} ms</td>
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
    return <div className="rounded-lg border bg-white p-4 text-sm animate-pulse">Analysing… ({doc.status})</div>;
  if (doc.status === "failed")
    return <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">Analysis failed: {doc.error}</div>;
  const s = doc.risk_score ?? 0;
  const color = doc.risk_band === "high" ? "#e11d48" : doc.risk_band === "medium" ? "#d97706" : "#059669";
  return (
    <div className="rounded-lg border bg-white p-4 space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-500">Risk score</div>
          <div className="text-4xl font-semibold tabular-nums" style={{ color }}>{s.toFixed(2)}</div>
        </div>
        <div className="text-right text-xs text-slate-500">
          coverage {pct(doc.coverage ?? 0)}<br />{doc.page_count} page(s) · {doc.kind.toUpperCase()}
        </div>
      </div>
      <div className="h-2 rounded bg-slate-100 overflow-hidden">
        <div className="h-full" style={{ width: pct(s), background: color }} />
      </div>
      <p className="text-xs text-slate-500">
        Probabilistic indicator from heuristic detectors, not a verdict. Scores are uncalibrated.
      </p>
      {doc.needs_review && (
        <div className="rounded bg-amber-50 p-2 text-xs text-amber-800">
          Routed to human review: {doc.review_reasons.join("; ")}
        </div>
      )}
    </div>
  );
}

function ReviewForm({ doc, onDone }: { doc: DocumentDetail; onDone: (d: DocumentDetail) => void }) {
  const [decision, setDecision] = useState("inconclusive");
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
    <form onSubmit={submit} className="rounded-lg border bg-white p-4 space-y-2 text-sm">
      <h2 className="font-semibold">Human review</h2>
      {last && <p className="text-xs text-slate-600">Last decision: <b>{last.decision}</b>{last.reviewer && ` by ${last.reviewer}`} — {last.notes}</p>}
      <div className="flex gap-2">
        {["authentic", "tampered", "inconclusive"].map((d) => (
          <label key={d} className={`flex-1 cursor-pointer rounded border px-2 py-1 text-center ${decision === d ? "bg-slate-900 text-white" : ""}`}>
            <input type="radio" className="hidden" name="decision" value={d} checked={decision === d} onChange={() => setDecision(d)} />{d}
          </label>
        ))}
      </div>
      <textarea className="w-full rounded border px-2 py-1" rows={3} placeholder="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={5000} />
      {err && <p className="text-rose-700 text-xs">{err}</p>}
      <button disabled={busy} className="rounded bg-slate-900 px-3 py-1.5 text-white disabled:opacity-50">Submit review</button>
    </form>
  );
}
