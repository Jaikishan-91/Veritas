# Architecture

## System Overview
```
React (pdf.js, overlays) --HTTP--> FastAPI --> PostgreSQL (documents, findings, artifacts, reviews)
                                      |    \-> MinIO (originals, heatmaps)
                                      \-> Analysis pipeline (in-process thread pool)
```

## Components
- `backend/app/api.py` — REST routes (documents, artifacts, reviews).
- `backend/app/storage.py` — `ObjectStore` protocol; `MinioStore` (prod), `LocalStore` (tests/dev).
- `backend/app/db.py` — SQLAlchemy models + session.
- `backend/app/analysis/`
  - `ingest.py` — sniff the type from magic bytes and build a `DocumentContext`: raw bytes, kind, page rasters (RGB numpy), and the PyMuPDF doc for PDFs.
  - `detectors/` — each detector exposes `name`, `requires` and `run(ctx) -> list[Finding]` and may attach artifacts.
    - `pdf_metadata` — Info vs XMP, editor tools in producer/creator, create/modify dates, incremental updates (`%%EOF` count).
    - `pdf_structure` — invisible text (render mode 3), text covered by filled shapes (white-box overlays), annotations, text-layer vs. glyph-coverage checks.
    - `font_consistency` — per-line font family/size/subset-prefix anomalies (PyMuPDF spans); the same base font with different subset tags means the text was edited.
    - `image_metadata` — EXIF software/editor tags, date inconsistencies, JPEG quality estimate.
    - `ela` — Error Level Analysis heatmap and outlier region boxes (raster; any input).
    - `noise` — blockwise noise-residual inconsistency used to flag splicing (raster).
    - `copy_move` — ORB keypoint self-matching with offset clustering (raster).
    - `ocr_text` — optional PaddleOCR. Flags per-line character-height and baseline anomalies, and PDF text-layer vs OCR disagreement.
  - `fusion.py` — weighted noisy-OR -> risk score; band and review routing.
  - `pipeline.py` — orchestrates ingest -> detectors -> fusion. A failure in one detector is isolated and lowers coverage.

## Data Flow
1. `POST /api/documents` validates the upload, stores the original in the object store, inserts a `documents` row (`queued`), and submits the job.
2. The worker loads bytes, runs the pipeline, stores artifacts (PNG heatmaps), and writes findings, score and status.
3. The UI polls `GET /api/documents/{id}`, renders the original (pdf.js for PDFs, `<img>` otherwise) and draws normalized bboxes and heatmaps.
4. If `needs_review` is set, the document appears in `GET /api/reviews`. A reviewer posts a decision.

## Coordinates
All bboxes are normalized `[x0,y0,x1,y1]` in [0,1] relative to the page (origin top-left). That keeps them independent of render DPI and pdf.js scale.
