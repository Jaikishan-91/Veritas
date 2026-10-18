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

export type Role = "analyst" | "reviewer" | "admin";
export interface User { id: string; email: string; role: Role; active: boolean; created_at: string }

/** Fired on any 401 so the app can drop back to the login screen. */
export const UNAUTHORIZED = "veritas:unauthorized";

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Requested-With", "veritas"); // CSRF guard required by the API for writes
  const r = await fetch(path, { ...init, headers, credentials: "same-origin" });
  if (r.status === 401 && !path.endsWith("/auth/login")) window.dispatchEvent(new Event(UNAUTHORIZED));
  if (r.status === 204) return undefined as T;
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join("; ") : body.detail;
    throw new Error(detail ?? `${r.status} ${r.statusText}`);
  }
  return r.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

export const api = {
  login: (email: string, password: string) => req<User>("/api/auth/login", json("POST", { email, password })),
  logout: () => req<void>("/api/auth/logout", { method: "POST" }),
  me: () => req<User>("/api/auth/me"),
  users: () => req<User[]>("/api/users"),
  createUser: (body: { email: string; password: string; role: Role }) => req<User>("/api/users", json("POST", body)),
  updateUser: (id: string, body: Partial<{ role: Role; active: boolean; password: string }>) =>
    req<User>(`/api/users/${id}`, json("PATCH", body)),
  upload(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    return req<DocumentSummary>("/api/documents", { method: "POST", body: fd });
  },
  list: () => req<DocumentSummary[]>("/api/documents"),
  get: (id: string) => req<DocumentDetail>(`/api/documents/${id}`),
  reviews: () => req<DocumentSummary[]>("/api/reviews"),
  review: (id: string, body: { decision: string; notes: string }) =>
    req<Review>(`/api/documents/${id}/reviews`, json("POST", body)),
};
