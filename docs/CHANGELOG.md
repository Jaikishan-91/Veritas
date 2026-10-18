# Changelog

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
