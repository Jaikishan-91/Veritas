from __future__ import annotations

import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from .config import get_settings


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16))
    mime: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_band: Mapped[str | None] = mapped_column(String(16))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_reasons: Mapped[list] = mapped_column(JSON, default=list)
    coverage: Mapped[float | None] = mapped_column(Float)
    page_count: Mapped[int | None] = mapped_column(Integer)
    page_sizes: Mapped[list] = mapped_column(JSON, default=list)
    detector_runs: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    findings: Mapped[list[FindingRow]] = relationship(back_populates="document", cascade="all, delete-orphan",
                                                      order_by="desc(FindingRow.contribution)")
    artifacts: Mapped[list[ArtifactRow]] = relationship(cascade="all, delete-orphan")
    reviews: Mapped[list[Review]] = relationship(cascade="all, delete-orphan", order_by="Review.created_at")


class FindingRow(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    detector: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    severity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    contribution: Mapped[float] = mapped_column(Float)
    page: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    document: Mapped[Document] = relationship(back_populates="findings")


class ArtifactRow(Base):
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    page: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64), default="image/png")


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(16))
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    url = get_settings().database_url
    kw = {}
    if url.startswith("sqlite"):
        Path(url.split("///", 1)[-1]).parent.mkdir(parents=True, exist_ok=True)
        kw["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, pool_pre_ping=True, **kw)
    Base.metadata.create_all(engine)  # ADR-005: no migrations for MVP
    return sessionmaker(engine, expire_on_commit=False)


def get_db():
    with get_sessionmaker()() as s:
        yield s
