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
        className={`block cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition
          ${drag ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white hover:border-slate-400"}`}
      >
        <input type="file" accept={ACCEPT} className="hidden" disabled={busy} onChange={(e) => send(e.target.files?.[0])} />
        <p className="text-lg font-medium">{busy ? "Uploading…" : "Drop a document or click to choose"}</p>
        <p className="mt-1 text-sm text-slate-500">PDF, PNG or JPG · up to 25 MB</p>
      </label>
      {error && <p className="rounded bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      <section>
        <h2 className="mb-3 font-semibold">Your documents</h2>
        <DocTable docs={docs} empty="No documents analysed yet." />
      </section>
    </div>
  );
}
