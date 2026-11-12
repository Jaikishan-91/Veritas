from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import worker
from .analysis.ingest import MIME, IngestError, sniff
from .auth import can_see, current_user, require_reviewer
from .config import get_settings
from .db import ArtifactRow, Document, Review, User, get_db
from .notifications import notify_review, send_notification_email
from .storage import get_store

router = APIRouter(prefix="/api")


class FindingOut(BaseModel):
    id: int
    detector: str
    category: str
    severity: float
    confidence: float
    contribution: float
    page: int | None
    bbox: list[float] | None
    description: str
    evidence: dict


class ArtifactOut(BaseModel):
    id: int
    kind: str
    page: int
    url: str


class ReviewIn(BaseModel):
    decision: Literal["accepted", "rejected", "inconclusive"]  # accepted = authentic, rejected = tampered
    notes: str = Field("", max_length=5000)


class ReviewOut(ReviewIn):
    id: int
    reviewer: str  # email of the authenticated reviewer (organisation or admin)
    created_at: datetime


class DocumentSummary(BaseModel):
    id: str
    filename: str
    kind: str
    size: int
    status: str
    risk_score: float | None
    risk_band: str | None
    needs_review: bool
    reviewed: bool
    decision: str | None  # latest review decision
    organisation: str | None  # username of the organisation it was submitted to
    created_at: datetime


class DocumentOut(DocumentSummary):
    sha256: str
    error: str | None
    review_reasons: list[str]
    coverage: float | None
    page_count: int | None
    page_sizes: list[list[float]]
    detector_runs: list[dict]
    file_url: str
    findings: list[FindingOut]
    artifacts: list[ArtifactOut]
    reviews: list[ReviewOut]


def _summary(d: Document, db: Session) -> dict:
    org = db.get(User, d.organisation_id) if d.organisation_id else None
    return dict(id=d.id, filename=d.filename, kind=d.kind, size=d.size, status=d.status, risk_score=d.risk_score,
                risk_band=d.risk_band, needs_review=d.needs_review, reviewed=bool(d.reviews),
                decision=d.reviews[-1].decision if d.reviews else None,
                organisation=(org.username or org.email) if org else None, created_at=d.created_at)


def _get(db: Session, doc_id: str, user: User) -> Document:
    d = db.get(Document, doc_id)
    if d is None or not can_see(user, d):
        raise HTTPException(404, "Document not found")  # 404, not 403: don't reveal other users' documents
    return d


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/documents", response_model=DocumentSummary, status_code=201)
async def upload(file: UploadFile = File(...), organisation_id: str | None = Form(None),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    if organisation_id:
        org = db.get(User, organisation_id)
        if org is None or org.role != "organisation" or not (org.approved and org.active) or org.id == user.id:
            raise HTTPException(422, "Unknown or unapproved organisation")
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File exceeds {get_settings().max_upload_mb} MB")
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        kind = sniff(data)
    except IngestError as e:
        raise HTTPException(415, str(e)) from e
    doc = Document(filename=(file.filename or "upload")[:255], kind=kind, mime=MIME[kind], size=len(data),
                   sha256=hashlib.sha256(data).hexdigest(), storage_key="", owner_id=user.id,
                   organisation_id=organisation_id or None)
    db.add(doc)
    db.flush()
    doc.storage_key = f"originals/{doc.id}"
    get_store().put(doc.storage_key, data, doc.mime)
    db.commit()
    worker.submit(doc.id)
    db.refresh(doc)
    return _summary(doc, db)


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(limit: int = 50, offset: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = (select(Document).where(Document.owner_id == user.id)  # everyone lists only their own documents
         .order_by(Document.created_at.desc()).limit(min(limit, 200)).offset(offset))
    return [_summary(d, db) for d in db.scalars(q)]


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _get(db, doc_id, user)
    return {
        **_summary(d, db), "sha256": d.sha256, "error": d.error, "review_reasons": d.review_reasons or [],
        "coverage": d.coverage, "page_count": d.page_count, "page_sizes": d.page_sizes or [],
        "detector_runs": d.detector_runs or [], "file_url": f"/api/documents/{d.id}/file",
        "findings": [FindingOut.model_validate(f, from_attributes=True) for f in d.findings],
        "artifacts": [{"id": a.id, "kind": a.kind, "page": a.page, "url": f"/api/documents/{d.id}/artifacts/{a.id}"}
                      for a in d.artifacts],
        "reviews": [ReviewOut.model_validate(r, from_attributes=True) for r in d.reviews],
    }


@router.get("/documents/{doc_id}/file")
def get_file(doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _get(db, doc_id, user)
    return Response(get_store().get(d.storage_key), media_type=d.mime,
                    headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff",
                             "Content-Security-Policy": "sandbox"})


@router.get("/documents/{doc_id}/artifacts/{artifact_id}")
def get_artifact(doc_id: str, artifact_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _get(db, doc_id, user)
    a = db.get(ArtifactRow, artifact_id)
    if a is None or a.document_id != doc_id:
        raise HTTPException(404, "Artifact not found")
    return Response(get_store().get(a.storage_key), media_type=a.content_type,
                    headers={"Cache-Control": "private, max-age=3600"})


@router.get("/reviews", response_model=list[DocumentSummary])
def review_queue(include_reviewed: bool = False, user: User = Depends(require_reviewer),
                 db: Session = Depends(get_db)):
    # organisations: everything submitted to them; admins: everything the system routed for review (ADR-015)
    where = Document.organisation_id == user.id if user.role == "organisation" else Document.needs_review.is_(True)
    q = select(Document).where(where).order_by(Document.risk_score.desc().nulls_first())
    docs = db.scalars(q).all()
    return [_summary(d, db) for d in docs if include_reviewed or not d.reviews]


@router.post("/documents/{doc_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(doc_id: str, body: ReviewIn, background: BackgroundTasks,
               user: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    d = _get(db, doc_id, user)
    if d.status in ("queued", "processing"):
        raise HTTPException(409, "Analysis still in progress")
    r = Review(document_id=d.id, reviewer=user.email, **body.model_dump())
    db.add(r)
    db.flush()
    mail = notify_review(db, d, r)
    db.commit()
    if mail:
        background.add_task(send_notification_email, *mail)  # after the response; failure is logged only
    return r
