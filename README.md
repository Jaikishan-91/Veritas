# Veritas — Document Integrity Analyzer

Gives each document a **risk score in [0,1]**, **localised suspicious regions** (bboxes and heatmaps), and an **interpretable evidence list** for PDF, PNG and JPG. It does not give a fake/real verdict. Uncertain cases are routed to a human review queue.

## Quick start (Docker)
```bash
cp .env.example .env        # set ADMIN_EMAIL / ADMIN_PASSWORD and other credentials
docker compose up -d --build
# UI: http://localhost:8080   API: http://localhost:8000/docs   MinIO console: http://localhost:9001
```
New users **sign up** at /signup with an email, a username and a password, and verify with a 6-digit code sent to their email; they can then log in with either email or username. Configure `SMTP_*` in `.env`; without SMTP, codes appear in `docker compose logs backend`. For a local test inbox, run `docker compose --profile mailpit up -d` with `SMTP_HOST=mailpit SMTP_PORT=1025 SMTP_SECURITY=none` and open http://localhost:8025.

Roles (ADR-015):
- **user**: uploads documents and sees only their own. On upload they can optionally pick an approved **organisation** to submit the document to.
- **organisation**: one login per organisation; signs up via the "Organisation" option on /signup and must be **approved by an admin** (Users page) before it can review or be chosen on upload. It sees and reviews every document submitted to it, whatever the score.
- **admin**: manages users and approvals, and reviews documents the system flags for review (uncertain score, low coverage, failed detector).

When an organisation or admin accepts or rejects a document, the owner is notified in-app (bell icon) and by email. The first admin is created from `ADMIN_EMAIL`/`ADMIN_PASSWORD` only when no users exist. Set `COOKIE_SECURE=true` behind HTTPS.

The UI has a light/dark toggle (follows the OS until changed). `/` is the public landing page; signed-in users work from `/dashboard`.

Schema changes are applied in place at backend startup (added columns and value renames, `backend/app/db.py`); there are no Alembic migrations yet. Do **not** run `docker compose down -v` to upgrade: it deletes the database and uploaded files. Only databases created before authentication (ADR-009) cannot be upgraded in place.

Set `WITH_OCR=1` in `.env` to bake PaddleOCR into the backend image (about 2.5 GB; first build takes several minutes, later code-only rebuilds reuse the dependency layer). OCR adds roughly 8 s per page on CPU; models download once into the `ocrmodels` volume. Without it, the `ocr_text` detector reports `unavailable` and coverage drops.

## Local dev
```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # add ,ocr for PaddleOCR
VERITAS_BOOTSTRAP_ADMIN_EMAIL=admin@example.com VERITAS_BOOTSTRAP_ADMIN_PASSWORD=change-me-admin \
  .venv/Scripts/uvicorn app.main:app --reload      # SQLite + ./data/objects by default
.venv/Scripts/python -m pytest -q
cd ../frontend && npm i && npm run dev             # http://localhost:5173, proxies /api -> :8000
```
After changing detectors or fusion, re-score stored documents: `docker compose exec backend python -m app.rescore` (`--all` also retries failed ones).

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
| ocr_text | text_tampering | all (optional, `WITH_OCR=1`) | OCR vs PDF text layer mismatch (ignores text inside embedded images), row character-height outliers |

Fusion: `score = 1 - prod_detectors(1 - noisyOR(top-5 w*severity*confidence))`. ELA and noise ("splicing") are combined and capped at 0.2 unless two detectors flag overlapping regions (ADR-014). See `docs/DECISIONS.md`.
Scores are **heuristic and uncalibrated** until the labelled-data phase (`docs/ROADMAP.md`).

Docs: `docs/` (requirements, architecture, decisions, blockers, roadmap).
