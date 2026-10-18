"""Shared raster helpers for block statistics, robust scoring and region extraction."""
from __future__ import annotations

import cv2
import numpy as np

from .types import norm_bbox


def block_mean(a: np.ndarray, b: int) -> np.ndarray:
    h, w = (a.shape[0] // b) * b, (a.shape[1] // b) * b
    a = a[:h, :w]
    return a.reshape(h // b, b, w // b, b).mean(axis=(1, 3))


def robust_z(x: np.ndarray, valid: np.ndarray | None = None) -> np.ndarray:
    vals = x[valid] if valid is not None else x.ravel()
    if vals.size == 0:
        return np.zeros_like(x)
    med = np.median(vals)
    mad = np.median(np.abs(vals - med)) * 1.4826
    if mad < 1e-6:
        mad = max(np.std(vals), 1e-6)
    z = (x - med) / mad
    if valid is not None:
        z = np.where(valid, z, 0.0)
    return z


def regions(mask: np.ndarray, z: np.ndarray, block: int, img_w: int, img_h: int,
            min_blocks: int = 4, max_frac: float = 0.4) -> list[dict]:
    """Connected components of a block mask -> normalized boxes with stats."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    total = mask.size
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_blocks or area > max_frac * total:
            continue
        zs = z[labels == i]
        out.append({
            "bbox": norm_bbox(x * block, y * block, (x + w) * block, (y + h) * block, img_w, img_h),
            "blocks": int(area),
            "mean_z": float(np.mean(zs)),
            "max_z": float(np.max(zs)),
        })
    out.sort(key=lambda r: r["mean_z"] * r["blocks"], reverse=True)
    return out


def heatmap_png(score: np.ndarray, out_w: int, out_h: int) -> bytes:
    """Map a [0,1] block score to an RGBA PNG whose alpha follows intensity (for overlays)."""
    s = np.clip(score, 0, 1)
    s = cv2.resize(s.astype(np.float32), (out_w, out_h), interpolation=cv2.INTER_LINEAR)
    color = cv2.applyColorMap((s * 255).astype(np.uint8), cv2.COLORMAP_JET)  # BGR
    alpha = (np.clip(s * 1.5, 0, 1) * 200).astype(np.uint8)
    bgra = np.dstack([color, alpha])
    ok, buf = cv2.imencode(".png", bgra)
    assert ok
    return buf.tobytes()


def downscale(img: np.ndarray, max_side: int = 2000) -> np.ndarray:
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    if s >= 1:
        return img
    return cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
