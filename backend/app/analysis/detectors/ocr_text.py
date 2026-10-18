"""OCR-based text checks (optional PaddleOCR).

- Row-level character-height anomalies (a field re-typed at a different size).
- PDF text layer vs. rendered OCR disagreement (hidden/mismatched text) and visible text with no text layer.
"""
from __future__ import annotations

import difflib
from typing import Callable

import numpy as np
import pymupdf

from ..types import DetectorOutput, DetectorUnavailable, DocumentContext, Finding, norm_bbox

# engine(rgb) -> list of (x0, y0, x1, y1, text, score) in pixel coords
OcrEngine = Callable[[np.ndarray], list[tuple[float, float, float, float, str, float]]]
_engine: OcrEngine | None = None


def set_engine(engine: OcrEngine | None) -> None:
    global _engine
    _engine = engine


def _paddle_engine() -> OcrEngine:
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise DetectorUnavailable(f"PaddleOCR not installed: {e}") from e
    ocr = PaddleOCR(lang="en")

    def run(rgb: np.ndarray):
        boxes = []
        if hasattr(ocr, "predict"):  # PaddleOCR >= 3.x
            for res in ocr.predict(rgb[:, :, ::-1]):
                for poly, text, score in zip(res["rec_polys"], res["rec_texts"], res["rec_scores"]):
                    p = np.asarray(poly)
                    boxes.append((p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max(), text, float(score)))
        else:  # 2.x
            for line in (ocr.ocr(rgb[:, :, ::-1], cls=False) or [[]])[0] or []:
                p = np.asarray(line[0])
                boxes.append((p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max(), line[1][0], float(line[1][1])))
        return boxes

    return run


def get_engine() -> OcrEngine:
    global _engine
    if _engine is None:
        _engine = _paddle_engine()
    return _engine


class OcrText:
    name = "ocr_text"

    def applies(self, ctx: DocumentContext) -> bool:
        return True

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        engine = get_engine()
        out = DetectorOutput()
        for pno, rgb in enumerate(ctx.pages):
            h, w = rgb.shape[:2]
            lines = [l for l in engine(rgb) if l[4].strip() and l[5] >= 0.5]
            out.notes[f"page_{pno}_lines"] = len(lines)
            self._height_anomalies(lines, pno, w, h, out)
            if ctx.kind == "pdf":
                self._layer_mismatch(ctx.pdf[pno], lines, pno, w, h, out)
        return out

    def _height_anomalies(self, lines, pno, w, h, out):
        rows: list[list] = []
        for l in sorted(lines, key=lambda l: (l[1] + l[3]) / 2):
            cy = (l[1] + l[3]) / 2
            if rows and abs(cy - rows[-1][0]) < 0.4 * (l[3] - l[1]):
                rows[-1][1].append(l)
            else:
                rows.append([cy, [l]])
        for _, row in rows:
            if len(row) < 3:
                continue
            hs = np.array([l[3] - l[1] for l in row])
            med = np.median(hs)
            for l, hh in zip(row, hs):
                if abs(hh / med - 1) > 0.3:
                    out.findings.append(Finding(
                        self.name, "text_tampering", 0.3, 0.35,
                        f"Text '{l[4][:40]}' has a character height {hh / med:.0%} of neighbouring text on the same row",
                        page=pno, bbox=norm_bbox(*l[:4], w, h), evidence={"text": l[4][:200], "height_ratio": round(float(hh / med), 2)}))

    def _layer_mismatch(self, page, lines, pno, w, h, out):
        sx, sy = page.rect.width / w, page.rect.height / h
        has_layer = bool(page.get_text("text").strip())
        if not has_layer:
            return  # scanned/flattened PDF: OCR is the only text source
        for x0, y0, x1, y1, text, _ in lines:
            layer = page.get_textbox(pymupdf.Rect(x0 * sx, y0 * sy, x1 * sx, y1 * sy)).strip()
            norm = lambda s: "".join(s.split()).lower()  # noqa: E731
            if not layer:
                if len(norm(text)) >= 4:
                    out.findings.append(Finding(
                        self.name, "text_tampering", 0.4, 0.45,
                        f"Visible text '{text[:40]}' has no text layer on an otherwise digital page (pasted image/vector text?)",
                        page=pno, bbox=norm_bbox(x0, y0, x1, y1, w, h), evidence={"ocr_text": text[:200]}))
                continue
            ratio = difflib.SequenceMatcher(None, norm(text), norm(layer)).ratio()
            if ratio < 0.5:
                out.findings.append(Finding(
                    self.name, "text_tampering", 0.6, 0.5,
                    "Displayed text differs from the PDF text layer at the same position",
                    page=pno, bbox=norm_bbox(x0, y0, x1, y1, w, h),
                    evidence={"ocr_text": text[:200], "layer_text": layer[:200], "similarity": round(ratio, 2)}))
