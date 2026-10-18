"""In-process analysis worker (ADR-002)."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import select

from .analysis.ingest import IngestError
from .analysis.pipeline import analyze
from .config import get_settings
from .db import ArtifactRow, Document, FindingRow, get_sessionmaker
from .storage import get_store

log = logging.getLogger(__name__)


@lru_cache
def _pool() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=max(get_settings().workers, 1), thread_name_prefix="analysis")


def submit(doc_id: str) -> None:
    if get_settings().workers == 0:  # synchronous mode (tests / debugging)
        process(doc_id)
    else:
        _pool().submit(process, doc_id)


def resume_pending() -> None:
    with get_sessionmaker()() as s:
        ids = s.scalars(select(Document.id).where(Document.status.in_(("queued", "processing")))).all()
    for i in ids:
        submit(i)


def process(doc_id: str) -> None:
    store = get_store()
    with get_sessionmaker()() as s:
        doc = s.get(Document, doc_id)
        if doc is None:
            return
        doc.status = "processing"
        s.commit()
        try:
            result = analyze(store.get(doc.storage_key))
            # idempotent on retry
            doc.findings.clear()
            doc.artifacts.clear()
            for i, a in enumerate(result.artifacts):
                key = f"artifacts/{doc.id}/{a.kind}_p{a.page}_{i}.png"
                store.put(key, a.png, "image/png")
                doc.artifacts.append(ArtifactRow(kind=a.kind, page=a.page, storage_key=key))
            for f in result.findings:
                doc.findings.append(FindingRow(
                    detector=f.detector, category=f.category, severity=f.severity, confidence=f.confidence,
                    contribution=f.contribution, page=f.page, bbox=f.bbox, description=f.description,
                    evidence=f.evidence))
            doc.risk_score = result.fusion.score
            doc.risk_band = result.fusion.band
            doc.needs_review = result.fusion.needs_review
            doc.review_reasons = result.fusion.review_reasons
            doc.coverage = result.coverage
            doc.page_count = result.total_pages
            doc.page_sizes = [list(p) for p in result.page_sizes]
            doc.detector_runs = result.detector_runs
            doc.status, doc.error = "completed", None
        except IngestError as e:
            doc.status, doc.error = "failed", str(e)
        except Exception as e:  # noqa: BLE001
            log.exception("analysis failed for %s", doc_id)
            doc.status, doc.error = "failed", f"Internal analysis error: {type(e).__name__}"
            doc.needs_review, doc.review_reasons = True, ["analysis failed"]
        doc.completed_at = datetime.now(timezone.utc)
        s.commit()
