from app.analysis.fusion import fuse
from app.analysis.types import Finding


def f(det, cat, sev, conf=1.0):
    return Finding(det, cat, sev, conf, "x")


def test_empty_is_zero():
    r = fuse([], coverage=1.0, errors=0)
    assert r.score == 0 and r.band == "low" and not r.needs_review


def test_bounded_and_monotonic():
    a = fuse([f("d1", "structure", 0.5)], 1.0, 0).score
    b = fuse([f("d1", "structure", 0.5), f("d2", "metadata", 0.5)], 1.0, 0).score
    assert 0 < a < b <= 1


def test_many_weak_hits_do_not_saturate():
    r = fuse([f("d", "font_mismatch", 0.3, 0.5) for _ in range(100)], 1.0, 0)
    assert r.score < 0.5


def test_review_routing():
    assert fuse([f("d", "text_tampering", 0.6, 0.8)], 1.0, 0).needs_review  # mid-band
    assert fuse([], 0.5, 0).needs_review  # low coverage
    assert fuse([], 1.0, 1).needs_review  # detector error


def test_repeated_hits_from_one_detector_decay():
    one = fuse([f("font", "font_mismatch", 0.45, 0.55)], 1.0, 0).score
    five = fuse([f("font", "font_mismatch", 0.45, 0.55) for _ in range(5)], 1.0, 0).score
    assert five < 2 * one  # corroboration, not linear accumulation
    assert five < 0.35  # design-level noise alone must not reach the high band


def _at(det, bbox, sev=1.0, conf=0.5):
    x = Finding(det, "splicing", sev, conf, "x", page=0, bbox=bbox)
    return x


def test_uncorroborated_splicing_is_capped():
    r = fuse([_at("ela", [0.1, 0.1, 0.3, 0.3]) for _ in range(5)], 1.0, 0)
    assert r.score <= 0.2 and r.band == "low"


def test_corroborated_splicing_counts_fully():
    box = [0.1, 0.1, 0.3, 0.3]
    alone = fuse([_at("ela", box)], 1.0, 0).score
    both = fuse([_at("ela", box), _at("noise", [0.12, 0.12, 0.32, 0.32])], 1.0, 0).score
    apart = fuse([_at("ela", box), _at("noise", [0.6, 0.6, 0.8, 0.8])], 1.0, 0).score
    assert both > 0.2 >= apart >= alone
