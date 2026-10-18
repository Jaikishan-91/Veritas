"""EXIF / PNG text / XMP checks for raster inputs."""
from __future__ import annotations

import re
from datetime import datetime

from ..types import DetectorOutput, DocumentContext, Finding

EDITORS = ["photoshop", "gimp", "paint.net", "pixelmator", "affinity", "snapseed", "picsart", "canva",
           "lightroom", "fotor", "photopea", "krita", "paintshop", "inpaint"]
SOFTWARE, DATETIME, MAKE, MODEL = 305, 306, 271, 272
EXIF_IFD, DT_ORIGINAL = 0x8769, 36867


def _dt(s) -> datetime | None:
    try:
        return datetime.strptime(str(s).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def jpeg_quality(img) -> int | None:
    """Rough libjpeg-style quality estimate from the luminance quantization table."""
    q = getattr(img, "quantization", None)
    if not q or 0 not in q:
        return None
    avg = sum(q[0]) / len(q[0])
    # libjpeg standard luminance table average is ~57.6 at quality 50
    scale = avg / 57.625 * 100
    quality = (200 - scale) / 2 if scale <= 100 else 5000 / scale
    return int(max(1, min(100, round(quality))))


class ImageMetadata:
    name = "image_metadata"

    def applies(self, ctx: DocumentContext) -> bool:
        return ctx.kind in ("png", "jpeg")

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        out = DetectorOutput()
        img = ctx.image
        exif = img.getexif()
        software = str(exif.get(SOFTWARE) or img.info.get("Software") or img.info.get("software") or "")
        modified = _dt(exif.get(DATETIME))
        original = _dt(exif.get_ifd(EXIF_IFD).get(DT_ORIGINAL)) if exif else None
        out.notes = {"software": software, "make": str(exif.get(MAKE) or ""), "model": str(exif.get(MODEL) or ""),
                     "datetime": str(modified) if modified else None, "datetime_original": str(original) if original else None}
        if ctx.kind == "jpeg":
            out.notes["jpeg_quality_estimate"] = jpeg_quality(img)

        def add(sev, conf, desc, **ev):
            out.findings.append(Finding(self.name, "metadata", sev, conf, desc, page=0, evidence=ev))

        hit = [e for e in EDITORS if e in software.lower()]
        if hit:
            add(0.45, 0.6, f"Image saved by editing software: {software}", software=software)
        if modified and original:
            delta = (modified - original).total_seconds()
            if delta < -60:
                add(0.5, 0.65, "EXIF modify time precedes capture time", datetime=str(modified), original=str(original))
            elif delta > 3600:
                add(0.3, 0.5, "Image modified after capture (EXIF DateTime later than DateTimeOriginal)",
                    datetime=str(modified), original=str(original))

        xmp = ctx.data[: 2_000_000]
        if b"<x:xmpmeta" in xmp:
            actions = re.findall(rb"stEvt:action[=\">\s]+(\w+)", xmp)
            tools = sorted({t.decode(errors="ignore") for t in re.findall(rb"stEvt:softwareAgent[=\">\s]+\"?([^\"<]+)", xmp)})
            edits = [a.decode() for a in actions if a in (b"saved", b"edited", b"derived", b"converted")]
            if edits:
                add(0.4, 0.55, f"XMP edit history records {len(edits)} save/edit event(s)", actions=edits[:20], tools=tools[:5])
            if not hit and any(e in " ".join(tools).lower() for e in EDITORS):
                add(0.4, 0.55, "XMP history names editing software", tools=tools[:5])
        return out
