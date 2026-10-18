"""Copy-move (cloning) via ORB self-matching and clustering of displacement vectors."""
from __future__ import annotations

from collections import Counter

import cv2
import numpy as np
import pymupdf

from ..raster import downscale
from ..types import DetectorOutput, DocumentContext, Finding, clamp01, norm_bbox

MIN_MATCHES, MIN_SHIFT, BIN = 10, 30, 6


def clone_clusters(gray: np.ndarray) -> list[dict]:
    orb = cv2.ORB_create(nfeatures=5000, fastThreshold=5)
    kp, des = orb.detectAndCompute(gray, None)
    if des is None or len(kp) < 2 * MIN_MATCHES:
        return []
    knn = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(des, des, k=4)
    pairs = {}
    for ms in knn:
        ms = [m for m in ms if m.trainIdx != m.queryIdx]
        if len(ms) < 2:
            continue
        a, b = ms[0], ms[1]
        if a.distance > 40 or a.distance > 0.75 * b.distance:
            continue
        p, q = np.array(kp[a.queryIdx].pt), np.array(kp[a.trainIdx].pt)
        if np.linalg.norm(q - p) < MIN_SHIFT:
            continue
        if (q[0] - p[0], q[1] - p[1]) < (0, 0):  # canonical direction
            p, q = q, p
        pairs[tuple(sorted((a.queryIdx, a.trainIdx)))] = (p, q)
    keyed = [((round((q[0] - p[0]) / BIN), round((q[1] - p[1]) / BIN)), p, q) for p, q in pairs.values()]
    counts = Counter(k for k, _, _ in keyed)
    clusters, used = [], set()
    for key, _ in counts.most_common():
        if key in used:
            continue
        near = {(key[0] + i, key[1] + j) for i in (-1, 0, 1) for j in (-1, 0, 1)} - used
        members = [(p, q) for k, p, q in keyed if k in near]
        used |= near
        if len(members) < MIN_MATCHES:
            continue
        src, dst = np.array([m[0] for m in members]), np.array([m[1] for m in members])
        if src.std(axis=0).max() < 3:  # degenerate single-point cluster
            continue
        clusters.append({"n": len(members), "src": src, "dst": dst, "offset": (dst - src).mean(axis=0)})
    return clusters


def _box(pts: np.ndarray, pad: float = 8) -> tuple[float, float, float, float]:
    return pts[:, 0].min() - pad, pts[:, 1].min() - pad, pts[:, 0].max() + pad, pts[:, 1].max() + pad


class CopyMove:
    name = "copy_move"

    def applies(self, ctx: DocumentContext) -> bool:
        return True

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        out = DetectorOutput()
        for pno, rgb in enumerate(ctx.pages):
            img = downscale(rgb, 1600)
            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            for c in clone_clusters(gray)[:5]:
                sb, db = norm_bbox(*_box(c["src"]), w, h), norm_bbox(*_box(c["dst"]), w, h)
                if ctx.kind == "pdf" and self._vector_text_repeat(ctx, pno, sb, db):
                    continue
                out.findings.append(Finding(
                    self.name, "copy_move", clamp01(0.4 + 0.01 * c["n"]), 0.6,
                    f"Region appears duplicated elsewhere on the page ({c['n']} matching keypoints, same displacement)",
                    page=pno, bbox=db,
                    evidence={"source_bbox": sb, "matches": c["n"],
                              "offset_px": [round(float(v), 1) for v in c["offset"]]}))
        return out

    @staticmethod
    def _vector_text_repeat(ctx, pno, sb, db) -> bool:
        """Repeated live text in a vector PDF (e.g. identical table cells) is not image cloning."""
        page = ctx.pdf[pno]
        W, H = page.rect.width, page.rect.height
        texts = [page.get_textbox(pymupdf.Rect(b[0] * W, b[1] * H, b[2] * W, b[3] * H)).strip() for b in (sb, db)]
        return all(texts)
