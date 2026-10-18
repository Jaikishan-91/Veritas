# API
Interactive docs: `GET /docs` (FastAPI OpenAPI).

Authentication (ADR-009): `POST /api/auth/login` sets the httpOnly cookie `veritas_session`. Every request except `/api/health` and login needs it, and non-GET requests must also send the header `X-Requested-With: <any>`. 401 = not logged in or session expired; 403 = wrong role or missing CSRF header.
Roles: analyst (own documents), reviewer (all documents and reviews), admin (reviewer plus users).

Auth endpoints:
- `POST /api/auth/login` `{email, password}` -> user. Returns 401 for bad credentials and 429 after 5 failures in 15 min
- `POST /api/auth/logout` -> 204 (revokes the session)
- `GET  /api/auth/me` -> `{id, email, role, active, created_at}`
- `GET  /api/users` (admin), `POST /api/users` `{email, password>=10, role}` (admin, 409 on duplicate), `PATCH /api/users/{id}` `{role?, active?, password?}` (admin; deactivation or a password change revokes sessions; admins cannot demote or deactivate themselves)

Endpoints:
- `GET  /api/health`
- `POST /api/documents` multipart `file` -> 201 summary. Errors: 400 empty, 413 too large, 415 unsupported type
- `GET  /api/documents?limit&offset` -> summaries (analysts: own only; another user's document returns 404)
- `GET  /api/documents/{id}` -> detail: score, band, needs_review, review_reasons, coverage, page_sizes, detector_runs, findings[], artifacts[], reviews[]
- `GET  /api/documents/{id}/file` -> original bytes (`CSP: sandbox`, `nosniff`)
- `GET  /api/documents/{id}/artifacts/{artifact_id}` -> PNG heatmap (RGBA)
- `GET  /api/reviews?include_reviewed=false` -> review queue (reviewer/admin)
- `POST /api/documents/{id}/reviews` `{decision: authentic|tampered|inconclusive, notes}` -> 201 (reviewer/admin; `reviewer` is set from the session). Returns 409 while analysis is running

Finding: `{detector, category, severity, confidence, contribution, page (0-based), bbox [x0,y0,x1,y1] normalized top-left | null, description, evidence{}}`

