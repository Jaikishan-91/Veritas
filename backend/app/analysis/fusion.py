"""Evidence fusion: weighted noisy-OR per detector, then across detectors (ADR-001)."""
from __future__ import annotations

from dataclasses import dataclass

from .types import Finding

CATEGORY_WEIGHT = {
    "structure": 0.8,
    "text_tampering": 0.9,
    "font_mismatch": 0.7,
    "copy_move": 0.8,
    "splicing": 0.6,
    "metadata": 0.5,
}
TOP_K = 5  # cap per-detector evidence so many weak hits don't saturate the score


@dataclass
class FusionResult:
    score: float
    band: str
    needs_review: bool
    review_reasons: list[str]


def _noisy_or(ps: list[float]) -> float:
    r = 1.0
    for p in ps:
        r *= 1.0 - p
    return 1.0 - r


def fuse(findings: list[Finding], coverage: float, errors: int, *, band_medium=0.3, band_high=0.6,
         review_low=0.3, review_high=0.7, min_coverage=0.75) -> FusionResult:
    by_det: dict[str, list[Finding]] = {}
    for f in findings:
        f.contribution = round(CATEGORY_WEIGHT.get(f.category, 0.5) * f.severity * f.confidence, 4)
        by_det.setdefault(f.detector, []).append(f)
    per_det = [_noisy_or([f.contribution for f in sorted(fs, key=lambda f: -f.contribution)[:TOP_K]])
               for fs in by_det.values()]
    score = round(_noisy_or(per_det), 4)
    band = "high" if score >= band_high else "medium" if score >= band_medium else "low"
    reasons = []
    if review_low <= score < review_high:
        reasons.append("score in uncertainty band")
    if coverage < min_coverage:
        reasons.append(f"detector coverage {coverage:.0%} below {min_coverage:.0%}")
    if errors:
        reasons.append(f"{errors} detector(s) failed")
    return FusionResult(score, band, bool(reasons), reasons)
