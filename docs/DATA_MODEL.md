# Data Model
See backend/app/db/models.py.

Entities:
- documents(id uuid, filename, kind, mime, size, sha256, storage_key, status, error, risk_score, risk_band, needs_review, review_reasons json, coverage, page_count, page_sizes json, detector_runs json, created_at, completed_at)
- findings(id, document_id fk, detector, category, severity, confidence, contribution, page, bbox json, description, evidence json)
- artifacts(id, document_id fk, kind, page, storage_key, content_type)
- reviews(id, document_id fk, decision, notes, reviewer, created_at)

Relationships: document 1-* findings, artifacts, reviews.
