# Changelog

## 2026-10-18 — Authentication
Added: cookie-session auth, analyst/reviewer/admin roles, per-owner document isolation, admin user management API and UI, login page, login throttling, CSRF header check, bootstrap admin from env.
Changed: review `reviewer` comes from the session (request field removed). `documents.owner_id` added, so existing databases need a reset.
Verified: `pytest` 29 passed (8 new auth tests: unauthenticated 401, lockout 429, cookie flags, logout revocation, CSRF 403, analyst isolation 404, role 403s, user management with session revocation). `npm run build` OK. Docker end-to-end via nginx: anonymous 401, admin creates analyst, analyst uploads and views own document (score 0.685), analyst gets 403 on reviews and on upload without the CSRF header, admin sees the document, logout then 401, cookie is HttpOnly on /api.
Not verified: login and users pages in a real browser.

## 2026-10-18 — MVP
Added:
- Backend: ingest (magic-byte sniffing, PDF render, image load) and 8 detectors (pdf_metadata, pdf_structure, font_consistency, image_metadata, ela, noise, copy_move, ocr_text [optional]). Also noisy-OR fusion with band and review routing.
- API: upload, document detail, original file, artifacts, review queue, reviews. SQLAlchemy models (Postgres/SQLite), MinIO/local object store, in-process worker with resume on restart.
- Frontend: upload page, pdf.js/image viewer with bbox, source-bbox and heatmap overlays, evidence list ranked by contribution, detector run table, review form and queue.
- Docker Compose: postgres, minio (Chainguard image), backend, frontend (nginx).

Verified:
- `pytest`: 23 passed (detectors on synthetic tampered PDF, copy-move PNG and spliced JPEG; fusion; API flow; limits).
- `npm run build`: type-check and build OK.
- `docker compose up --build`: the tampered PDF scored 0.685/high and the clone PNG 0.482/medium (review). Security headers checked.

Not verified: PaddleOCR with the real library; UI rendering in a browser (the build is served, but the page was not visually inspected); real-world accuracy.
