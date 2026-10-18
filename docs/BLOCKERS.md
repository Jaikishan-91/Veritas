# Blockers
Open Blockers:
- Login throttling is in-memory and per process. It resets on restart and is not shared across replicas. Move it to Postgres/Redis before scaling out.
- Schema changes (such as the new `documents.owner_id`) need a DB reset until Alembic is added (ADR-005).
- PaddleOCR integration has not been verified. `ocr_text` was tested only with an injected fake engine, and the PaddleOCR 2.x/3.x adapter has not been run.
- Detector thresholds were tuned only on synthetic fixtures. Precision/recall on real documents is unknown and needs a labelled dataset.

Resolved Blockers:
- 2026-10-18 No authentication: added cookie sessions with analyst/reviewer/admin roles (ADR-009).
- 2026-10-18 The `minio/minio` image cannot be pulled. Switched to the Chainguard image (ADR-007).
