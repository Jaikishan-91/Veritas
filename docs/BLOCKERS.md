# Blockers
Open Blockers:
- Login throttling is in-memory and per process. It resets on restart and is not shared across replicas. Move it to Postgres/Redis before scaling out.
- Schema changes need a DB reset until Alembic is added (ADR-005). This has caused data loss twice (auth, then OTP/sign-up), so adding Alembic is now urgent.
- Real SMTP delivery depends on the operator's provider credentials. Only Mailpit and the console fallback were tested.
- Sign-up has no per-IP rate limit or CAPTCHA. The per-address resend cooldown prevents mail-bombing one address, but not mass sign-ups to many addresses.
- PaddleOCR integration has not been verified. `ocr_text` was tested only with an injected fake engine, and the PaddleOCR 2.x/3.x adapter has not been run.
- Detector thresholds were tuned only on synthetic fixtures. Precision/recall on real documents is unknown and needs a labelled dataset.

Resolved Blockers:
- 2026-10-18 No authentication: added cookie sessions with analyst/reviewer/admin roles (ADR-009).
- 2026-10-18 The `minio/minio` image cannot be pulled. Switched to the Chainguard image (ADR-007).
