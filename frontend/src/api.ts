export type BBox = [number, number, number, number];

export interface Finding {
  id: number;
  detector: string;
  category: string;
  severity: number;
  confidence: number;
  contribution: number;
  page: number | null;
  bbox: BBox | null;
  description: string;
  evidence: Record<string, unknown>;
}

export interface ArtifactRef { id: number; kind: string; page: number; url: string }
export interface Review { id: number; decision: string; notes: string; reviewer: string; created_at: string }

export interface DocumentSummary {
  id: string;
  filename: string;
  kind: "pdf" | "png" | "jpeg";
  size: number;
  status: "queued" | "processing" | "completed" | "failed";
  risk_score: number | null;
  risk_band: "low" | "medium" | "high" | null;
  needs_review: boolean;
  reviewed: boolean;
  created_at: string;
}

export interface DetectorRun { detector: string; status: string; findings?: number; error?: string; ms: number }

export interface DocumentDetail extends DocumentSummary {
  sha256: string;
  error: string | null;
  review_reasons: string[];
  coverage: number | null;
  page_count: number | null;
  page_sizes: [number, number][];
  detector_runs: DetectorRun[];
  file_url: string;
  findings: Finding[];
  artifacts: ArtifactRef[];
  reviews: Review[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail ?? `${r.status} ${r.statusText}`);
  }
  return r.json();
}

export const api = {
  upload(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    return req<DocumentSummary>("/api/documents", { method: "POST", body: fd });
  },
  list: () => req<DocumentSummary[]>("/api/documents"),
  get: (id: string) => req<DocumentDetail>(`/api/documents/${id}`),
  reviews: () => req<DocumentSummary[]>("/api/reviews"),
  review: (id: string, body: { decision: string; notes: string; reviewer: string }) =>
    req<Review>(`/api/documents/${id}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
