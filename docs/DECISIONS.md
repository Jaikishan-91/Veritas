# Architecture & Engineering Decisions

ADR-001 — Heuristic detectors + noisy-OR fusion for MVP
Date: 2026-10-18
Context: No labelled training data yet. The output has to be interpretable.
Decision: Classical forensic heuristics (ELA, noise residual, ORB copy-move, PDF structure/metadata/font checks) with per-category weights fused by noisy-OR: `score = 1 - prod(1 - w * severity * confidence)`. Every term maps to a finding. Calibration is deferred to the dataset phase.

ADR-002 — In-process worker for MVP
Date: 2026-10-18
Context: Async analysis is needed, and a broker (Celery/Redis) adds operational surface.
Decision: Use a single-thread `ThreadPoolExecutor` inside the API process (PyMuPDF is not thread-safe, so do not raise `VERITAS_WORKERS` above 1; scale with replicas/processes). Status lives in Postgres; on startup, jobs left `queued`/`processing` are re-submitted. Swap to a queue (RQ/Celery/Arq) when scaling out.

ADR-003 — Normalized bbox coordinates
Date: 2026-10-18
Decision: Findings store `[x0,y0,x1,y1]` in [0,1], top-left origin, so the overlay is independent of DPI and viewer scale.

ADR-004 — PaddleOCR optional
Date: 2026-10-18
Context: paddlepaddle is large and its platform wheel support varies.
Decision: Install it as an optional extra (`pip install .[ocr]`; Docker build arg `WITH_OCR=1`). If import fails, `ocr_text` is reported as not run. Lower detector coverage pushes the case toward review.

ADR-005 — Schema via SQLAlchemy `create_all` for MVP
Date: 2026-10-18
Decision: Skip Alembic until the schema stabilizes. Add migrations before the first production deployment (ROADMAP).

ADR-006 — Visual detectors always run on rasters
Date: 2026-10-18
Context: FR9 requires robustness to conversion and flattening.
Decision: PDFs are rendered at 150 DPI. Raster detectors run on every page (capped at `MAX_PAGES`) in addition to structural checks.

ADR-007 — MinIO image source
Date: 2026-10-18
Context: `minio/minio` on Docker Hub no longer pulls ("pull access denied"); `quay.io/minio/minio` returned 401 (verified 2026-10-18).
Decision: Default to `cgr.dev/chainguard/minio:latest`, overridable with `MINIO_IMAGE`. That image has no shell or `mc`, so compose has no healthcheck for it. The backend creates its store lazily and retries on the next request.

ADR-008 — Ingest resource limits
Date: 2026-10-18
Decision: Images over 60 MP are rejected. PDF pages are rendered with the longest side capped at 4000 px. Uploads are capped at 25 MB, and at most 20 pages are analysed. A document with more pages than that is routed to review. Original files are served with `CSP: sandbox` and `nosniff`.
