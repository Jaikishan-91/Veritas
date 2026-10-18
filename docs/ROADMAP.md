# Roadmap
Current (MVP):
- [x] Backend analysis core (detectors + fusion) with tests
- [x] API, storage, DB, review queue
- [x] Frontend (upload, viewer w/ overlays, review queue)
- [x] Docker Compose (postgres, minio, backend, frontend)
- [ ] Verify PaddleOCR in the `WITH_OCR=1` image (adapter written, not yet run against the real library)
- [x] Authentication: cookie sessions, roles, admin user management (ADR-009)
- [x] Self sign-up with emailed OTP; landing page and home dashboard; owner-only visibility (ADR-010/011)

Next:
- **Alembic migrations (urgent: schema resets caused data loss)**; password reset via OTP; sign-up rate limiting/CAPTCHA; audit log; shared login throttle; password-reset/SSO (OIDC); external job queue (RQ/Celery) / process-based workers
- Calibration on labelled data (e.g. CASIA, Columbia, DocTamper, synthetic PDF edits); per-detector thresholds from ROC

Later:
- Office formats (python-docx, openpyxl): docProps, revision history, font runs
- PDF digital signature validation (pyHanko), incl. modification-after-signing
- Learned detectors (e.g. TruFor / CAT-Net style) and validated explainability
