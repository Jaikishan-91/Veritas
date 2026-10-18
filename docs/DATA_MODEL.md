# Data Model
See backend/app/db/models.py.

Entities:
- users(id uuid, email unique, password_hash scrypt, role analyst|reviewer|admin, active, email_verified, created_at)
- otp_codes(id, user_id fk, purpose, code_hash hmac-sha256, attempts, consumed, created_at, expires_at)
- sessions(token_hash sha256 pk, user_id fk, created_at, expires_at)
- documents(id uuid, owner_id fk users nullable, filename, kind, mime, size, sha256, storage_key, status, error, risk_score, risk_band, needs_review, review_reasons json, coverage, page_count, page_sizes json, detector_runs json, created_at, completed_at)
- findings(id, document_id fk, detector, category, severity, confidence, contribution, page, bbox json, description, evidence json)
- artifacts(id, document_id fk, kind, page, storage_key, content_type)
- reviews(id, document_id fk, decision, notes, reviewer, created_at)

Relationships: document 1-* findings, artifacts, reviews; user 1-* documents (owner), sessions.
