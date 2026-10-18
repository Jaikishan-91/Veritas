# API
Interactive docs: `GET /docs` (FastAPI OpenAPI).

Endpoints:
- `GET  /api/health`
- `POST /api/documents` multipart `file` -> 201 summary. Errors: 400 empty, 413 too large, 415 unsupported type
- `GET  /api/documents?limit&offset` -> summaries
- `GET  /api/documents/{id}` -> detail: score, band, needs_review, review_reasons, coverage, page_sizes, detector_runs, findings[], artifacts[], reviews[]
- `GET  /api/documents/{id}/file` -> original bytes (`CSP: sandbox`, `nosniff`)
- `GET  /api/documents/{id}/artifacts/{artifact_id}` -> PNG heatmap (RGBA)
- `GET  /api/reviews?include_reviewed=false` -> review queue
- `POST /api/documents/{id}/reviews` `{decision: authentic|tampered|inconclusive, notes, reviewer}` -> 201. Returns 409 while analysis is running

Finding: `{detector, category, severity, confidence, contribution, page (0-based), bbox [x0,y0,x1,y1] normalized top-left | null, description, evidence{}}`

Authentication: none (see BLOCKERS.md).
