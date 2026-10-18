# Veritas — Document Integrity Analyzer

Gives each document a **risk score in [0,1]**, **localised suspicious regions** (bboxes and heatmaps), and an **interpretable evidence list** for PDF, PNG and JPG. It does not give a fake/real verdict. Uncertain cases are routed to a human review queue.

## Quick start (Docker)
```bash
cp .env.example .env        # set ADMIN_EMAIL / ADMIN_PASSWORD and other credentials
docker compose up -d --build
# UI: http://localhost:8080   API: http://localhost:8000/docs   MinIO console: http://localhost:9001
```
Sign in with `ADMIN_EMAIL`/`ADMIN_PASSWORD`, then add analysts/reviewers under **Users**. The first admin is created only when no users exist. Set `COOKIE_SECURE=true` behind HTTPS. Upgrading from a pre-auth database requires `docker compose down -v` (no migrations yet).

Set `WITH_OCR=1` in `.env` to bake PaddleOCR into the backend image. Without it, the `ocr_text` detector reports `unavailable` and coverage drops.

## Local dev
```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # add ,ocr for PaddleOCR
VERITAS_BOOTSTRAP_ADMIN_EMAIL=admin@example.com VERITAS_BOOTSTRAP_ADMIN_PASSWORD=change-me-admin \
  .venv/Scripts/uvicorn app.main:app --reload      # SQLite + ./data/objects by default
.venv/Scripts/python -m pytest -q
cd ../frontend && npm i && npm run dev             # http://localhost:5173, proxies /api -> :8000
```
Configuration uses `VERITAS_*` environment variables (see `backend/app/config.py`).

## Detectors (MVP)
| Detector | Category | Inputs | Signal |
|---|---|---|---|
| pdf_metadata | metadata | PDF | editor tools, date inconsistencies, XMP vs Info, incremental updates |
| pdf_structure | text_tampering / structure | PDF | text hidden under opaque shapes (white-box), overwrite, invisible text, overlay annotations |
| font_consistency | font_mismatch | PDF | per-visual-line font/size/baseline/colour outliers, multiple subsets of one font |
| image_metadata | metadata | PNG/JPG | EXIF/PNG editor software, EXIF date inconsistencies, XMP edit history |
| ela | splicing | all rasters | recompression error, edge-normalised, plus heatmap |
| noise | splicing | all rasters | local noise-level inconsistency, plus heatmap |
| copy_move | copy_move | all rasters | ORB self-matching with displacement clustering (source and target boxes) |
| ocr_text | text_tampering | all (optional) | OCR vs PDF text layer mismatch, row character-height outliers |

Fusion: `score = 1 - prod_detectors(1 - noisyOR(top-5 w*severity*confidence))`. See `docs/DECISIONS.md`.
Scores are **heuristic and uncalibrated** until the labelled-data phase (`docs/ROADMAP.md`).

Docs: `docs/` (requirements, architecture, decisions, blockers, roadmap).
