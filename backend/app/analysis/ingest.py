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


def load(data: bytes, max_pages: int = 20, dpi: int = 150, max_pixels: int = 60_000_000,
         max_side: int = 4000) -> DocumentContext:
    kind = sniff(data)
    if kind == "pdf":
        return _load_pdf(data, max_pages, dpi, max_side)
    return _load_image(data, kind, max_pixels)


def _load_pdf(data: bytes, max_pages: int, dpi: int, max_side: int) -> DocumentContext:
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
        # cap raster size for oversized pages (memory / decompression-bomb guard)
        page_dpi = min(dpi, max_side * 72 / max(page.rect.width, page.rect.height, 1))
        pix = page.get_pixmap(dpi=max(int(page_dpi), 1), alpha=False, colorspace=pymupdf.csRGB)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        pages.append(arr)
        sizes.append((page.rect.width, page.rect.height))
    return DocumentContext(data=data, kind="pdf", pages=pages, page_sizes=sizes, pdf=doc, total_pages=doc.page_count)


def _load_image(data: bytes, kind: Kind, max_pixels: int) -> DocumentContext:
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > max_pixels:
            raise IngestError(f"Image too large ({img.width}x{img.height} px)")
        img.load()
    except IngestError:
        raise
    except Exception as e:  # noqa: BLE001
        raise IngestError(f"Unreadable image: {e}") from e
    rgb = np.array(img.convert("RGB"))
    return DocumentContext(data=data, kind=kind, pages=[rgb], page_sizes=[(img.width, img.height)], image=img)
