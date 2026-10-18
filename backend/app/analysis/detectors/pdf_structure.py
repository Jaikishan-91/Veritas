"""PDF content-stream structure checks: covered text, invisible text, overlay annotations."""
from __future__ import annotations

import pymupdf

from ..types import DetectorOutput, DocumentContext, Finding, norm_bbox

OVERLAY_ANNOTS = {"FreeText", "Stamp", "Square", "Ink", "Redact"}


def _area(r: pymupdf.Rect) -> float:
    return max(r.width, 0) * max(r.height, 0)


def _covers(a: pymupdf.Rect, b: pymupdf.Rect) -> bool:
    """`a` substantially overlaps `b`. Text rects are whole lines, so measure against the smaller rect."""
    inter = _area(a & b)
    return inter > 0 and inter > 0.5 * min(_area(a), _area(b)) and (a & b).height > 0.6 * b.height


def _merge(rects: list[pymupdf.Rect]) -> list[pymupdf.Rect]:
    merged: list[pymupdf.Rect] = []
    for r in rects:
        for m in merged:
            if m.intersects(r) or m.contains(r):
                m |= r
                break
        else:
            merged.append(pymupdf.Rect(r))
    return merged


class PdfStructure:
    name = "pdf_structure"

    def applies(self, ctx: DocumentContext) -> bool:
        return ctx.kind == "pdf"

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        out = DetectorOutput()
        for pno in range(len(ctx.pages)):
            page = ctx.pdf[pno]
            w, h = page.rect.width, page.rect.height
            self._covered_text(page, pno, w, h, out)
            self._invisible_text(page, pno, w, h, out)
            self._annotations(page, pno, w, h, out)
        return out

    def _covered_text(self, page, pno, w, h, out):
        """Opaque paths/images drawn after text and covering it — the classic white-box edit."""
        page_area = w * h
        texts: list[pymupdf.Rect] = []
        covers: list[dict] = []  # {"rect", "hidden": [Rect], "overwritten": bool}
        for kind, bbox in page.get_bboxlog():
            r = pymupdf.Rect(bbox)
            if _area(r) <= 0:
                continue
            if kind.endswith("-text"):
                for c in covers:
                    if _covers(c["rect"], r):
                        c["overwritten"] = True
                texts.append(r)
            elif kind in ("fill-path", "fill-image", "fill-shade") and _area(r) < 0.5 * page_area:
                hidden = [t for t in texts if _covers(r, t)]
                if hidden:
                    covers.append({"rect": r, "hidden": hidden, "overwritten": False})
        for c in covers:
            cover, hidden, overwritten = c["rect"], c["hidden"], c["overwritten"]
            sev = 0.75 if overwritten else 0.6
            desc = ("Text is hidden under an opaque shape and new text is drawn on top (overwrite)"
                    if overwritten else "Text is hidden beneath an opaque shape or image drawn later")
            hidden_text = page.get_textbox(cover).strip()[:200]
            out.findings.append(Finding(
                "pdf_structure", "text_tampering", sev, 0.8, desc, page=pno,
                bbox=norm_bbox(*cover, w, h),
                evidence={"hidden_text": hidden_text, "hidden_spans": len(hidden), "overwritten": overwritten}))

    def _invisible_text(self, page, pno, w, h, out):
        imgs = page.get_image_info()
        img_cover = sum(_area(pymupdf.Rect(i["bbox"]) & page.rect) for i in imgs) / max(w * h, 1)
        invisible = [pymupdf.Rect(s["bbox"]) for s in page.get_texttrace()
                     if s.get("type") == 3 or s.get("opacity", 1) == 0]
        if not invisible:
            return
        if img_cover > 0.6:
            out.notes.setdefault("ocr_layer_pages", []).append(pno)  # scanned page with OCR layer: normal
            return
        for r in _merge(invisible)[:10]:
            out.findings.append(Finding(
                "pdf_structure", "text_tampering", 0.5, 0.6,
                "Invisible text present on a non-scanned page (hidden content differs from what is displayed)",
                page=pno, bbox=norm_bbox(*r, w, h), evidence={"text": page.get_textbox(r).strip()[:200]}))

    def _annotations(self, page, pno, w, h, out):
        for a in page.annots() or []:
            t = a.type[1]
            if t in OVERLAY_ANNOTS:
                out.findings.append(Finding(
                    "pdf_structure", "structure", 0.35, 0.6,
                    f"{t} annotation overlays page content (may visually alter the document)",
                    page=pno, bbox=norm_bbox(*a.rect, w, h),
                    evidence={"annot_type": t, "content": (a.info.get("content") or "")[:200]}))
