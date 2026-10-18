from __future__ import annotations

import io

import pymupdf
import numpy as np
from PIL import Image

from .types import DocumentContext, Kind


class IngestError(ValueError):
    pass


MIME = {"pdf": "application/pdf", "png": "image/png", "jpeg": "image/jpeg"}


def sniff(data: bytes) -> Kind:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    # PDF header may be preceded by junk bytes; spec readers accept it within the first 1KB.
    if b"%PDF-" in data[:1024]:
        return "pdf"
    raise IngestError("Unsupported file type (expected PDF, PNG or JPEG)")


def load(data: bytes, max_pages: int = 20, dpi: int = 150) -> DocumentContext:
    kind = sniff(data)
    if kind == "pdf":
        return _load_pdf(data, max_pages, dpi)
    return _load_image(data, kind)


def _load_pdf(data: bytes, max_pages: int, dpi: int) -> DocumentContext:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:  # noqa: BLE001 - PyMuPDF raises various types
        raise IngestError(f"Unreadable PDF: {e}") from e
    if doc.needs_pass:
        raise IngestError("Encrypted PDF requires a password")
    if doc.page_count == 0:
        raise IngestError("PDF has no pages")
    pages, sizes = [], []
    for i in range(min(doc.page_count, max_pages)):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi, alpha=False, colorspace=pymupdf.csRGB)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        pages.append(arr)
        sizes.append((page.rect.width, page.rect.height))
    return DocumentContext(data=data, kind="pdf", pages=pages, page_sizes=sizes, pdf=doc, total_pages=doc.page_count)


def _load_image(data: bytes, kind: Kind) -> DocumentContext:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:  # noqa: BLE001
        raise IngestError(f"Unreadable image: {e}") from e
    rgb = np.array(img.convert("RGB"))
    return DocumentContext(data=data, kind=kind, pages=[rgb], page_sizes=[(img.width, img.height)], image=img)
