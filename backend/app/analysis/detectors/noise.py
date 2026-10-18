"""Local noise-level inconsistency (splicing cue). Residual = image - median filter, per-block level regressed on edges."""
from __future__ import annotations

import cv2
import numpy as np

from ..raster import block_mean, downscale, heatmap_png, regions, robust_z
from ..types import Artifact, DetectorOutput, DocumentContext, Finding, clamp01

BLOCK, Z_THR = 32, 3.5


class NoiseInconsistency:
    name = "noise"

    def applies(self, ctx: DocumentContext) -> bool:
        return True

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        out = DetectorOutput()
        for pno, rgb in enumerate(ctx.pages):
            img = downscale(rgb)
            gray8 = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            gray = gray8.astype(np.float32)
            resid = np.abs(gray - cv2.medianBlur(gray8, 3).astype(np.float32))
            grad = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
            n, g = block_mean(resid, BLOCK), block_mean(grad, BLOCK)
            sat = block_mean(((gray8 > 250) | (gray8 < 5)).astype(np.float32), BLOCK)
            valid = sat < 0.9
            if valid.sum() < 16 or np.median(n[valid]) < 0.3:
                out.notes.setdefault("skipped_pages", []).append(pno)  # digitally clean page: no noise floor
                continue
            ln = np.log(n + 0.05)
            a, b = np.polyfit(g[valid], ln[valid], 1)
            z = robust_z(ln - (a * g + b), valid)
            h, w = img.shape[:2]
            out.artifacts.append(Artifact("noise_heatmap", pno, heatmap_png(np.abs(z) / (2 * Z_THR), w, h)))
            mask = (np.abs(z) > Z_THR) & valid
            for r in regions(mask, np.abs(z), BLOCK, w, h, min_blocks=3, max_frac=0.5)[:5]:
                out.findings.append(Finding(
                    self.name, "splicing", clamp01(0.3 + 0.05 * (r["mean_z"] - Z_THR)), 0.45,
                    "Region has a noise level inconsistent with the rest of the page (possible splice)",
                    page=pno, bbox=r["bbox"], evidence={k: round(v, 2) if isinstance(v, float) else v
                                                        for k, v in r.items() if k != "bbox"}))
        return out
