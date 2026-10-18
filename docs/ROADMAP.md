# Roadmap
Current (MVP):
- [ ] Backend analysis core (detectors + fusion) with tests
- [ ] API, storage, DB, review queue
- [ ] Frontend (upload, viewer w/ overlays, review queue)
- [ ] Docker Compose (postgres, minio, backend, frontend)

Next:
- Alembic migrations; auth/RBAC for reviewers; external job queue (RQ/Celery)
- Calibration on labelled data (e.g. CASIA, Columbia, DocTamper, synthetic PDF edits)

Later:
- Office formats (python-docx, openpyxl): docProps, revision history, font runs
- PDF digital signature validation (pyHanko), incl. modification-after-signing
- Learned detectors (e.g. TruFor / CAT-Net style) and validated explainability
