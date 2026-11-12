import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type DocumentSummary } from "../api";
import { DocTable } from "../components/RiskBadge";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";

export default function UploadPage() {
  const nav = useNavigate();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);

  useEffect(() => { api.list().then(setDocs).catch((e) => setError(e.message)); }, []);

  async function send(file?: File) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const d = await api.upload(file);
      nav(`/documents/${d.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <label
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); send(e.dataTransfer.files[0]); }}
        className={`block cursor-pointer rounded-2xl border-2 border-dashed px-6 py-16 text-center transition-colors
          ${drag ? "border-brand bg-brand-soft" : "border-line bg-surface hover:border-brand"}`}
      >
        <input type="file" accept={ACCEPT} className="hidden" disabled={busy} onChange={(e) => send(e.target.files?.[0])} />
        <span className="mx-auto mb-4 grid size-12 place-items-center rounded-full bg-brand-soft text-brand">
          <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
          </svg>
        </span>
        <p className="text-lg font-medium">{busy ? "Uploading…" : "Drop a document or click to choose"}</p>
        <p className="mt-1 text-sm text-muted">PDF, PNG or JPG · up to 25 MB</p>
      </label>
      {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">{error}</p>}
      <section>
        <h2 className="mb-3 font-semibold">Your documents</h2>
        <DocTable docs={docs} empty="No documents analysed yet." />
      </section>
    </div>
  );
}
