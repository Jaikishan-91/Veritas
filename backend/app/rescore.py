"""Re-run analysis on stored documents after a scoring/detector change: `python -m app.rescore [--all]`.

Reuses worker.process, so findings and artifacts are replaced in place. Reviews and notifications are untouched.
By default only completed documents are re-scored; --all also retries failed ones.
"""
from __future__ import annotations

import argparse

from sqlalchemy import select

from .db import Document, get_sessionmaker
from .worker import process


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="include failed documents")
    args = ap.parse_args(argv)
    statuses = ("completed", "failed") if args.all else ("completed",)
    with get_sessionmaker()() as s:
        docs = s.execute(select(Document.id, Document.filename, Document.risk_score)
                         .where(Document.status.in_(statuses))).all()
    for doc_id, name, old in docs:
        process(doc_id)
        with get_sessionmaker()() as s:
            new = s.get(Document, doc_id)
            print(f"{name}: {old if old is None else round(old, 2)} -> "
                  f"{new.risk_score if new.risk_score is None else round(new.risk_score, 2)} ({new.status})")
    print(f"re-scored {len(docs)} document(s)")


if __name__ == "__main__":
    main()
