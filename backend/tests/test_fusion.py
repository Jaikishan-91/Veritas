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
