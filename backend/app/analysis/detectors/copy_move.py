"""Copy-move (cloning) via ORB self-matching and clustering of displacement vectors."""
from __future__ import annotations

from collections import Counter

import cv2
import numpy as np
import pymupdf

from ..raster import downscale
from ..types import DetectorOutput, DocumentContext, Finding, clamp01, norm_bbox

MIN_MATCHES, MIN_SHIFT, BIN = 10, 30, 6
MAX_SPAN = 0.5  # a cloned patch is compact; matches spread over half the page are repeated layout elements
MAX_SELF_OVERLAP = 0.3  # source overlapping its own copy = periodic texture/text, not a pasted patch
LAYOUT_CLUSTERS = 4  # more distinct displacement clusters than this = repetitive design (UI, tables, forms)
AXIS_PX = 2.0  # offset exactly along a row/column is the signature of grid layout


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


def _self_overlap(a, b) -> float:
    """Fraction of box `a` covered by box `b`."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix / max((a[2] - a[0]) * (a[3] - a[1]), 1e-6)


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
            clusters = clone_clusters(gray)
            boxes = [_box(c["src"]) for c in clusters]
            # Many displacement clusters, or one source matched at several offsets, = a repeated motif/grid, not a clone.
            repetitive = len(clusters) > LAYOUT_CLUSTERS or any(
                max(_self_overlap(a, b), _self_overlap(b, a)) > 0.5 for i, a in enumerate(boxes) for b in boxes[i + 1:])
            kept, limit = 0, 1 if repetitive else 5  # on a repetitive page further clusters are the same cue again
            for c, sbox in zip(clusters, boxes):
                if kept == limit:
                    break
                dbox = _box(c["dst"])
                span = max((sbox[2] - sbox[0]) / w, (sbox[3] - sbox[1]) / h)
                if _self_overlap(sbox, dbox) > MAX_SELF_OVERLAP or span > MAX_SPAN:
                    continue
                sb, db = norm_bbox(*sbox, w, h), norm_bbox(*dbox, w, h)
                if ctx.kind == "pdf" and self._vector_text_repeat(ctx, pno, sb, db):
                    continue
                kept += 1
                aligned = bool(min(abs(c["offset"][0]), abs(c["offset"][1])) < AXIS_PX)  # np.bool_ is not JSON-able
                conf = 0.2 if repetitive else 0.3 if aligned else 0.6
                desc = f"Region appears duplicated elsewhere on the page ({c['n']} matching keypoints, same displacement)"
                if aligned or repetitive:
                    desc += "; low confidence: repetition follows the page layout"
                out.findings.append(Finding(
                    self.name, "copy_move", clamp01(0.4 + 0.01 * c["n"]), conf, desc,
                    page=pno, bbox=db,
                    evidence={"source_bbox": sb, "matches": c["n"],
                              "offset_px": [round(float(v), 1) for v in c["offset"]],
                              "layout_aligned": aligned, "page_clusters": len(clusters)}))
        return out

    @staticmethod
    def _vector_text_repeat(ctx, pno, sb, db) -> bool:
        """Repeated live text in a vector PDF (e.g. identical table cells) is not image cloning."""
        page = ctx.pdf[pno]
        W, H = page.rect.width, page.rect.height
        texts = [page.get_textbox(pymupdf.Rect(b[0] * W, b[1] * H, b[2] * W, b[3] * H)).strip() for b in (sb, db)]
        return all(texts)
