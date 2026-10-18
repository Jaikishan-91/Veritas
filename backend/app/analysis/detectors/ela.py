"""Error Level Analysis. Recompression error is regressed on local edge energy so text edges don't dominate."""
from __future__ import annotations

import cv2
import numpy as np

from ..raster import block_mean, downscale, heatmap_png, regions, robust_z
from ..types import Artifact, DetectorOutput, DocumentContext, Finding, clamp01

BLOCK, QUALITY, Z_THR = 16, 90, 4.0


def ela_zmap(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ok, enc = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
    dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    ela = np.abs(bgr.astype(np.int16) - dec.astype(np.int16)).max(axis=2).astype(np.float32)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    grad = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    e, g = block_mean(ela, BLOCK), block_mean(grad, BLOCK)
    valid = (e > 0.5) | (g > 2)
    if valid.sum() < 20:
        return None
    a, b = np.polyfit(g[valid], e[valid], 1)
    z = robust_z(e - (a * g + b), valid)
    return z, valid


class ErrorLevelAnalysis:
    name = "ela"

    def applies(self, ctx: DocumentContext) -> bool:
        return True

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        out = DetectorOutput()
        conf = 0.5 if ctx.kind == "jpeg" else 0.35  # ELA is most meaningful on JPEG-compressed sources
        for pno, rgb in enumerate(ctx.pages):
            img = downscale(rgb)
            res = ela_zmap(img)
            if res is None:
                continue
            z, _ = res
            mask = cv2.morphologyEx((z > Z_THR).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            h, w = img.shape[:2]
            out.artifacts.append(Artifact("ela_heatmap", pno, heatmap_png(z / (2 * Z_THR), w, h)))
            for r in regions(mask, z, BLOCK, w, h)[:5]:
                out.findings.append(Finding(
                    self.name, "splicing", clamp01(0.3 + 0.05 * (r["mean_z"] - Z_THR)), conf,
                    "Region recompresses differently from the rest of the page (inconsistent compression history)",
                    page=pno, bbox=r["bbox"], evidence={k: round(v, 2) if isinstance(v, float) else v
                                                        for k, v in r.items() if k != "bbox"}))
        return out
