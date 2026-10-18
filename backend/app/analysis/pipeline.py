from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from ..config import Settings, get_settings
from . import ingest
from .detectors import Detector, all_detectors
from .fusion import FusionResult, fuse
from .types import Artifact, DetectorUnavailable, Finding

log = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    kind: str
    total_pages: int
    page_sizes: list[tuple[float, float]]
    findings: list[Finding]
    artifacts: list[Artifact]
    fusion: FusionResult
    coverage: float
    detector_runs: list[dict] = field(default_factory=list)


def analyze(data: bytes, settings: Settings | None = None, detectors: list[Detector] | None = None) -> AnalysisResult:
    s = settings or get_settings()
    ctx = ingest.load(data, max_pages=s.max_pages, dpi=s.render_dpi, max_pixels=s.max_image_pixels,
                      max_side=s.max_render_side)
    findings: list[Finding] = []
    artifacts: list[Artifact] = []
    runs = []
    applicable = ran = errors = 0
    for det in detectors if detectors is not None else all_detectors():
        if not det.applies(ctx):
            continue
        applicable += 1
        t0 = time.perf_counter()
        run = {"detector": det.name, "status": "ok"}
        try:
            out = det.run(ctx)
            findings += out.findings
            artifacts += out.artifacts
            run["findings"] = len(out.findings)
            run["notes"] = out.notes
            ran += 1
        except DetectorUnavailable as e:
            run.update(status="unavailable", error=str(e))
        except Exception as e:  # noqa: BLE001 - isolate detector failures
            log.exception("detector %s failed", det.name)
            run.update(status="error", error=f"{type(e).__name__}: {e}")
            errors += 1
        run["ms"] = round((time.perf_counter() - t0) * 1000)
        runs.append(run)
    coverage = ran / applicable if applicable else 0.0
    result = fuse(findings, coverage, errors, band_medium=s.band_medium, band_high=s.band_high,
                  review_low=s.review_low, review_high=s.review_high, min_coverage=s.min_coverage)
    if ctx.total_pages > len(ctx.pages):
        result.needs_review = True
        result.review_reasons.append(f"only first {len(ctx.pages)} of {ctx.total_pages} pages analysed")
    findings.sort(key=lambda f: -f.contribution)
    if ctx.pdf is not None:
        ctx.pdf.close()
    return AnalysisResult(ctx.kind, ctx.total_pages, ctx.page_sizes, findings, artifacts, result,
                          round(coverage, 3), runs)
