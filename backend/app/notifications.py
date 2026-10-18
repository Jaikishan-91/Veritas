"""In-app notifications (plus best-effort email) for review decisions."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .auth import current_user
from .db import Document, Notification, Review, User, get_db
from .mailer import MailError, send_email

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

DECISION_TEXT = {
    "accepted": "accepted. A reviewer found no evidence of tampering",
    "rejected": "rejected. A reviewer concluded the document was tampered with",
    "inconclusive": "marked inconclusive. A reviewer could not reach a decision",
}


class NotificationOut(BaseModel):
    id: int
    document_id: str | None
    kind: str
    message: str
    read: bool
    created_at: datetime


def notify_review(db: Session, doc: Document, review: Review) -> tuple[str, str, str] | None:
    """Create the owner's in-app notification; returns (to, subject, body) for the email, or None."""
    owner = db.get(User, doc.owner_id) if doc.owner_id else None
    if owner is None or owner.email == review.reviewer:  # no self-notification
        return None
    msg = f'Your document "{doc.filename}" was {DECISION_TEXT[review.decision]}.'
    if review.notes:
        msg += f" Reviewer notes: {review.notes[:500]}"
    db.add(Notification(user_id=owner.id, document_id=doc.id, kind=f"review_{review.decision}", message=msg))
    return owner.email, f"Veritas review: {doc.filename} {review.decision}", msg + "\n\nSign in to Veritas to see the details."


def send_notification_email(to: str, subject: str, body: str) -> None:
    try:
        send_email(to, subject, body)
    except MailError:
        log.warning("review notification email to %s failed; in-app notification still recorded", to)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50)
    return db.scalars(q).all()


@router.post("/notifications/{nid}/read", response_model=NotificationOut)
def mark_read(nid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, nid)
    if n is None or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.read = True
    db.commit()
    return n


@router.post("/notifications/read-all", status_code=204)
def mark_all_read(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(read=True))
    db.commit()
