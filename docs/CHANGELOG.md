# Changelog

## 2026-11-12 — Score recalibration, redesign with light/dark mode
Added: light/dark theme toggle (follows the OS by default, choice saved in localStorage, applied before first paint), semantic design tokens from the logo palette (`frontend/src/index.css`), logo in the headers and as favicon, `python -m app.rescore [--all]` to re-run analysis on stored documents.
Changed: all pages restyled (tokens instead of raw slate/white classes). copy_move drops clusters whose source overlaps its copy or spans more than half the page, and lowers confidence (and keeps one finding) on grid-aligned or repetitive pages. pdf_structure ignores filled paths that paint less than 80% of their bbox (table rules/borders). ELA/noise ("splicing") is capped at 0.2 unless two detectors flag overlapping regions (ADR-014).
Fixed: clean screenshots, logos, webcam photos and table-heavy PDFs scored high. Stored set of 14 documents re-scored: high-band count 7 to 1. The only remaining high is `tampered.pdf` (0.69, unchanged); `clone.png` is unchanged at 0.48; screenshots 0.61-0.72 to 0.15-0.25; VenturePath 0.81 to 0.34; AdmitCard 0.62 to 0.37 (ilovepdf metadata + ELA).
Verified: `pytest` 48 passed (4 new: uncorroborated splicing cap, corroborated splicing, layout-repetition copy-move, table borders; the last two fail against the previous detectors). `npm run build` OK. Docker rebuilt; re-score run on all 14 documents; frontend and `/logo.png` return 200.
Not verified: the redesigned UI in a browser (light and dark); detection on real-world splices, where ELA/noise alone now scores at most 0.2.

## 2026-10-18 — Review notifications, post-review access, role rename
Added: owner notifications for review decisions (header bell plus email), a decision banner on the document page, Pending/Reviewed tabs in the review queue, and the `decision` field on summaries.
Changed: decisions are `accepted`/`rejected`/`inconclusive` (were authentic/tampered/inconclusive). Role `analyst` is renamed `user`. Reviewers and admins keep access to reviewed documents. Existing rows are upgraded in place at startup (no DB reset).
Verified: `pytest` 44 passed (5 new: notification in-app and email, email failure isolation, post-review access, invalid decision and no self-notify, idempotent data upgrade). `npm run build` OK. Docker E2E (backend temporarily pointed at Mailpit, then restored to `.env` Gmail SMTP): existing analysts became `user`; the admin rejected a document; the owner got an unread `review_rejected` notification and an email in Mailpit; the summary shows `rejected`; the admin can still open the document and its file and sees it under Reviewed; role `analyst` is now 422.
Not verified: notification email through Gmail; the new UI in a browser.

## 2026-10-18 — Sign-up, OTP, home pages, visibility, font fix
Added: sign-up page with emailed 6-digit OTP verification (SMTP, or a console fallback), resend with cooldown, public landing page, logged-in home dashboard (Analyze moved to `/analyze`), optional Mailpit compose profile.
Changed: document visibility is owner-only, plus reviewers/admins for documents flagged for review (ADR-011). Font mismatch ignores page-design styles, and fusion decays repeated findings from one detector (ADR-012). Users have a new `email_verified` column and there is a new `otp_codes` table, so the DB was reset.
Fixed: clean documents with headings, labels and accent fonts no longer accumulate font-mismatch risk. The regression fixture had 7 false findings and now has 0.
Verified: `pytest` 39 passed (7 new sign-up/OTP tests, a visibility test, a styled-document regression test, a decay test). `npm run build` OK. Docker E2E: sign-up 202; login before verify 403; code received as email in Mailpit; verify 200 logs the user in. The owner sees their document. Admin's list is empty. Admin can open the flagged documents (and they appear in the queue), but gets 404 for the unflagged clean document and its file.
Not verified: delivery through a real SMTP provider; the new pages in a browser.
Incident: the DB reset in this change deleted user-uploaded documents and accounts. The model ran the data check and `docker compose down -v` in one command instead of stopping to review the check.

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
