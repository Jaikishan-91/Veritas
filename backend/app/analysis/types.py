from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

Category = Literal["text_tampering", "copy_move", "splicing", "font_mismatch", "metadata", "structure"]
Kind = Literal["pdf", "png", "jpeg"]


@dataclass
class Finding:
    detector: str
    category: Category
    severity: float  # how suspicious, if true [0,1]
    confidence: float  # how reliable this detector/observation is [0,1]
    description: str
    page: int | None = None  # 0-based
    bbox: list[float] | None = None  # normalized [x0,y0,x1,y1], top-left origin
    evidence: dict[str, Any] = field(default_factory=dict)
    contribution: float = 0.0  # filled by fusion


@dataclass
class Artifact:
    kind: str  # e.g. "ela_heatmap", "noise_heatmap"
    page: int
    png: bytes


@dataclass
class DetectorOutput:
    findings: list[Finding] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentContext:
    data: bytes
    kind: Kind
    pages: list[np.ndarray]  # RGB uint8 rasters, one per analysed page
    page_sizes: list[tuple[float, float]]  # native units (PDF points or pixels)
    pdf: Any = None  # pymupdf.Document for PDFs
    image: Any = None  # PIL.Image for raster inputs (original, for EXIF)
    total_pages: int = 1


class DetectorUnavailable(Exception):
    """Raised when an optional dependency for a detector is missing."""


def clamp01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def norm_bbox(x0: float, y0: float, x1: float, y1: float, w: float, h: float) -> list[float]:
    return [round(clamp01(x0 / w), 5), round(clamp01(y0 / h), 5), round(clamp01(x1 / w), 5), round(clamp01(y1 / h), 5)]
