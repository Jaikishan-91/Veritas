import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { BBox, Finding } from "../api";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

const CAT_COLOR: Record<string, string> = {
  text_tampering: "#e11d48",
  font_mismatch: "#d97706",
  copy_move: "#7c3aed",
  splicing: "#0891b2",
  structure: "#db2777",
  metadata: "#64748b",
};

export function usePdf(url: string | null) {
  const [doc, setDoc] = useState<pdfjs.PDFDocumentProxy | null>(null);
  useEffect(() => {
    if (!url) return;
    const task = pdfjs.getDocument({ url });
    task.promise.then(setDoc).catch(console.error);
    return () => { task.destroy(); };
  }, [url]);
  return doc;
}

function PdfCanvas({ pdf, pageNo, width }: { pdf: pdfjs.PDFDocumentProxy; pageNo: number; width: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let task: pdfjs.RenderTask | null = null;
    let cancelled = false;
    pdf.getPage(pageNo + 1).then((page) => {
      if (cancelled || !ref.current) return;
      const base = page.getViewport({ scale: 1 });
      const dpr = window.devicePixelRatio || 1;
      const viewport = page.getViewport({ scale: (width / base.width) * dpr });
      const canvas = ref.current;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      task = page.render({ canvas, viewport });
      task.promise.catch(() => {});
    });
    return () => { cancelled = true; task?.cancel(); };
  }, [pdf, pageNo, width]);
  return <canvas ref={ref} className="block w-full h-auto" />;
}

function Box({ b, color, dashed, active, label, onClick }: {
  b: BBox; color: string; dashed?: boolean; active?: boolean; label?: string; onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      title={label}
      className={`absolute cursor-pointer ${active ? "ring-4 ring-offset-1" : ""}`}
      style={{
        left: `${b[0] * 100}%`, top: `${b[1] * 100}%`,
        width: `${(b[2] - b[0]) * 100}%`, height: `${(b[3] - b[1]) * 100}%`,
        border: `2px ${dashed ? "dashed" : "solid"} ${color}`,
        background: active ? `${color}33` : `${color}14`,
        ["--tw-ring-color" as string]: `${color}88`,
      }}
    />
  );
}

export function PageView(props: {
  kind: string; fileUrl: string; pdf: pdfjs.PDFDocumentProxy | null; page: number; width: number;
  findings: Finding[]; heatmapUrl: string | null; heatOpacity: number;
  activeId: number | null; onSelect: (id: number) => void;
}) {
  const { kind, fileUrl, pdf, page, width, findings, heatmapUrl, heatOpacity, activeId, onSelect } = props;
  return (
    <div className="relative bg-white shadow border" style={{ width }}>
      {kind === "pdf"
        ? pdf ? <PdfCanvas pdf={pdf} pageNo={page} width={width} /> : <div className="h-96 grid place-items-center text-slate-400">Loading PDF…</div>
        : <img src={fileUrl} alt="document" className="block w-full h-auto" />}
      {heatmapUrl && (
        <img src={heatmapUrl} alt="heatmap" className="pointer-events-none absolute inset-0 w-full h-full" style={{ opacity: heatOpacity }} />
      )}
      {findings.filter((f) => f.bbox && f.page === page).map((f) => (
        <div key={f.id}>
          <Box b={f.bbox!} color={CAT_COLOR[f.category] ?? "#334155"} active={f.id === activeId}
               label={f.description} onClick={() => onSelect(f.id)} />
          {Array.isArray(f.evidence.source_bbox) && (
            <Box b={f.evidence.source_bbox as BBox} color={CAT_COLOR[f.category]} dashed active={f.id === activeId}
                 label={`Source of: ${f.description}`} onClick={() => onSelect(f.id)} />
          )}
        </div>
      ))}
    </div>
  );
}

export { CAT_COLOR };
