# API
Interactive docs: `GET /docs` (FastAPI OpenAPI).

Authentication (ADR-009): `POST /api/auth/login` sets the httpOnly cookie `veritas_session`. Every request except `/api/health` and login needs it, and non-GET requests must also send the header `X-Requested-With: <any>`. 401 = not logged in or session expired; 403 = wrong role or missing CSRF header.
Roles (ADR-015): user (own documents), organisation (own documents plus every document submitted to it, and its review queue, once an admin has approved it), admin (own documents plus flagged or reviewed documents, the flagged queue, and users). Lists always show only your own documents (ADR-011).

Auth endpoints:
- `POST /api/auth/login` `{email, password}` -> user. `email` may be an email or a username. Returns 401 for bad credentials, 403 `email_not_verified`, and 429 after 5 failures in 15 min
- `POST /api/auth/signup` `{email, username ^[A-Za-z0-9._-]{3,32}$, password>=10, account_type: user|organisation}` -> 202 and emails a 6-digit code. Organisations start with `approved=false`. Errors: 409 already verified or username taken, 403 sign-up disabled, 502 mail failure
- `POST /api/auth/verify` `{email, code}` -> user and session cookie. Returns 400 for an invalid, expired, used or over-attempted code
- `POST /api/auth/resend` `{email}` -> 202 always (60 s cooldown)
- `POST /api/auth/logout` -> 204 (revokes the session)
- `GET  /api/auth/me` -> `{id, email, username, role, active, approved, created_at}`
- `GET  /api/organisations` -> `[{id, username}]` approved, active organisations (any logged-in user)
- `GET  /api/users` (admin), `POST /api/users` `{email, username, password>=10, role: user|organisation|admin}` (admin, 409 on duplicate email or username; created organisations are approved), `PATCH /api/users/{id}` `{role?, active?, approved?, password?}` (admin; deactivation or a password change revokes sessions; admins cannot demote or deactivate themselves)

Endpoints:
- `GET  /api/health`
- `POST /api/documents` multipart `file`, optional `organisation_id` -> 201 summary (summaries include `organisation`, its username). Errors: 400 empty, 413 too large, 415 unsupported type, 422 not an approved organisation (or yourself)
- `GET  /api/documents?limit&offset` -> your own documents only. Opening another user's document returns 404 unless it was submitted to your approved organisation, or you are an admin and it is flagged or reviewed
- `GET  /api/documents/{id}` -> detail: score, band, needs_review, review_reasons, coverage, page_sizes, detector_runs, findings[], artifacts[], reviews[]
- `GET  /api/documents/{id}/file` -> original bytes (`CSP: sandbox`, `nosniff`)
- `GET  /api/documents/{id}/artifacts/{artifact_id}` -> PNG heatmap (RGBA)
- `GET  /api/reviews?include_reviewed=false` -> review queue: an approved organisation gets everything submitted to it, an admin gets flagged documents (403 for users and unapproved organisations); `true` also returns reviewed documents. Summaries include `decision` (latest)
- `POST /api/documents/{id}/reviews` `{decision: accepted|rejected|inconclusive, notes}` -> 201 (approved organisation or admin; `reviewer` is the session email). Returns 409 while analysis is running. The owner is notified in-app and by email
- `GET  /api/notifications` -> your latest 50 `{id, document_id, kind, message, read, created_at}`
- `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all` (204)

Finding: `{detector, category, severity, confidence, contribution, page (0-based), bbox [x0,y0,x1,y1] normalized top-left | null, description, evidence{}}`

