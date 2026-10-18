import pytest

from app.analysis import ingest
from app.analysis.detectors import ocr_text
from app.analysis.detectors.copy_move import CopyMove
from app.analysis.detectors.ela import ErrorLevelAnalysis
from app.analysis.detectors.font_consistency import FontConsistency, family
from app.analysis.detectors.image_metadata import ImageMetadata
from app.analysis.detectors.noise import NoiseInconsistency
from app.analysis.detectors.pdf_metadata import PdfMetadata, count_revisions, parse_pdf_date
from app.analysis.detectors.pdf_structure import PdfStructure
from app.analysis.pipeline import analyze


def iou_hit(bbox, px_box, w, h) -> bool:
    """True if a normalized bbox overlaps the expected pixel box."""
    x0, y0, x1, y1 = bbox[0] * w, bbox[1] * h, bbox[2] * w, bbox[3] * h
    ex0, ey0, ex1, ey1 = px_box
    return min(x1, ex1) > max(x0, ex0) and min(y1, ey1) > max(y0, ey0)


def test_sniff_rejects_unknown():
    with pytest.raises(ingest.IngestError):
        ingest.sniff(b"GIF89a....")


def test_pdf_date_parse():
    d = parse_pdf_date("D:20240320100000+05'30'")
    assert d.year == 2024 and d.utcoffset().total_seconds() == 19800


def test_font_family_normalization():
    assert family("ABCDEF+ArialMT") == family("Arial-BoldMT") == "arial"
    assert family("Helvetica") != family("Times-Roman")


def test_clean_pdf_has_no_structural_findings(clean_pdf):
    ctx = ingest.load(clean_pdf)
    assert PdfStructure().run(ctx).findings == []
    assert FontConsistency().run(ctx).findings == []
    assert PdfMetadata().run(ctx).findings == []
    assert count_revisions(clean_pdf) == 1


def test_tampered_pdf_detected(tampered_pdf):
    ctx = ingest.load(tampered_pdf)
    structure = PdfStructure().run(ctx).findings
    assert any(f.category == "text_tampering" and f.evidence["overwritten"] for f in structure)
    assert "1,250.00" in structure[0].evidence["hidden_text"]
    meta = PdfMetadata().run(ctx).findings
    descs = " ".join(f.description for f in meta)
    assert "incremental update" in descs and "pdfescape" in descs
    fonts = FontConsistency().run(ctx).findings
    assert any("9,250.00" in f.evidence.get("span_text", "") for f in fonts)


def test_copy_move_localized(copy_move_png):
    data, box = copy_move_png
    ctx = ingest.load(data)
    fs = CopyMove().run(ctx).findings
    assert fs, "expected a copy-move finding"
    h, w = ctx.pages[0].shape[:2]
    assert iou_hit(fs[0].bbox, box, w, h) or iou_hit(fs[0].evidence["source_bbox"], box, w, h)


def test_clean_texture_no_copy_move():
    from conftest import texture, to_bytes
    ctx = ingest.load(to_bytes(texture(seed=9), "PNG"))
    assert CopyMove().run(ctx).findings == []


def test_splice_localized(spliced_jpeg):
    data, box = spliced_jpeg
    ctx = ingest.load(data)
    h, w = ctx.pages[0].shape[:2]
    hits = [f for f in NoiseInconsistency().run(ctx).findings + ErrorLevelAnalysis().run(ctx).findings
            if iou_hit(f.bbox, box, w, h)]
    assert hits, "expected splice region to be flagged by noise or ELA"


def test_image_metadata_editor(photoshop_jpeg):
    fs = ImageMetadata().run(ingest.load(photoshop_jpeg)).findings
    assert any("Photoshop" in f.description for f in fs)


def test_ocr_layer_mismatch(clean_pdf):
    ctx = ingest.load(clean_pdf)
    h, w = ctx.pages[0].shape[:2]
    s = w / 595
    # fake OCR: sees a different amount where the text layer says 1,250.00
    ocr_text.set_engine(lambda rgb: [(150 * s, 162 * s, 200 * s, 174 * s, "9,999.99", 0.99)])
    fs = ocr_text.OcrText().run(ctx).findings
    assert any(f.evidence.get("layer_text") for f in fs)


def test_pipeline_scores(clean_pdf, tampered_pdf):
    clean, bad = analyze(clean_pdf), analyze(tampered_pdf)
    assert 0 <= clean.fusion.score < 0.3
    assert bad.fusion.score > 0.6 and bad.fusion.band == "high"
    assert bad.findings[0].contribution >= bad.findings[-1].contribution
    ocr_run = next(r for r in bad.detector_runs if r["detector"] == "ocr_text")
    assert ocr_run["status"] == "unavailable" and bad.coverage < 1


def test_clean_rasters_score_low():
    from conftest import jpeg_roundtrip, texture, to_bytes
    for data in (to_bytes(jpeg_roundtrip(texture(seed=5), 80), "JPEG", quality=80), to_bytes(texture(seed=6), "PNG")):
        r = analyze(data)
        assert r.fusion.score < 0.3, [(f.detector, f.description) for f in r.findings]


def test_image_pixel_limit():
    from conftest import texture, to_bytes
    with pytest.raises(ingest.IngestError, match="too large"):
        ingest.load(to_bytes(texture(), "PNG"), max_pixels=1000)


def test_pdf_render_capped():
    import pymupdf
    doc = pymupdf.open()
    doc.new_page(width=14400, height=14400)  # 200in square page
    ctx = ingest.load(doc.tobytes(), max_side=2000)
    assert max(ctx.pages[0].shape[:2]) <= 2000
