# Blockers
Open Blockers:
- No authentication or authorization. The API and review queue are open to anyone who can reach the port. Do not expose publicly until auth is added.
- PaddleOCR integration has not been verified. `ocr_text` was tested only with an injected fake engine, and the PaddleOCR 2.x/3.x adapter has not been run.
- Detector thresholds were tuned only on synthetic fixtures. Precision/recall on real documents is unknown and needs a labelled dataset.

Resolved Blockers:
- 2026-10-18 The `minio/minio` image cannot be pulled. Switched to the Chainguard image (ADR-007).
