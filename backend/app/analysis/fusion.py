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
DECAY = 0.5  # each further finding from the same detector counts half as much as the previous one
# Pixel-statistics cues (ELA, noise) fire on ordinary photos, screenshots and recompressed scans. On their own they
# are capped; they only count fully when two independent detectors flag overlapping regions on the same page.
UNCORROBORATED_CAP = {"splicing": 0.2}


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


def _overlap(a: Finding, b: Finding) -> bool:
    """Same page and the boxes share at least 30% of the smaller one (touching edges is not agreement)."""
    if a.page != b.page or not a.bbox or not b.bbox:
        return False
    iw = min(a.bbox[2], b.bbox[2]) - max(a.bbox[0], b.bbox[0])
    ih = min(a.bbox[3], b.bbox[3]) - max(a.bbox[1], b.bbox[1])
    if iw <= 0 or ih <= 0:
        return False
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])  # noqa: E731
    return iw * ih >= 0.3 * min(area(a.bbox), area(b.bbox))


def _corroborated(fs: list[Finding]) -> bool:
    return any(a.detector != b.detector and _overlap(a, b) for i, a in enumerate(fs) for b in fs[i + 1:])


def _detector_score(fs: list[Finding]) -> float:
    return _noisy_or([f.contribution * DECAY ** i for i, f in enumerate(sorted(fs, key=lambda f: -f.contribution)[:TOP_K])])


def fuse(findings: list[Finding], coverage: float, errors: int, *, band_medium=0.3, band_high=0.6,
         review_low=0.3, review_high=0.7, min_coverage=0.75) -> FusionResult:
    by_det: dict[str, list[Finding]] = {}
    weak: dict[str, list[Finding]] = {}
    for f in findings:
        f.contribution = round(CATEGORY_WEIGHT.get(f.category, 0.5) * f.severity * f.confidence, 4)
        if f.category in UNCORROBORATED_CAP:
            weak.setdefault(f.category, []).append(f)
        else:
            by_det.setdefault(f.detector, []).append(f)
    # Repeated hits from one detector are correlated (same cue), so they corroborate rather than multiply.
    per_det = [_detector_score(fs) for fs in by_det.values()]
    for cat, fs in weak.items():
        dets: dict[str, list[Finding]] = {}
        for f in fs:
            dets.setdefault(f.detector, []).append(f)
        family = _noisy_or([_detector_score(d) for d in dets.values()])
        per_det.append(family if _corroborated(fs) else min(family, UNCORROBORATED_CAP[cat]))
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
