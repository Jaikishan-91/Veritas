from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from ..types import DetectorOutput, DocumentContext, Finding

# Tools whose presence in Producer/Creator indicates post-generation editing rather than export.
EDITOR_TOOLS = [
    "photoshop", "illustrator", "inkscape", "gimp", "pdfescape", "sejda", "ilovepdf", "smallpdf",
    "pdf-xchange editor", "foxit phantompdf", "foxit pdf editor", "nitro pro", "pdfelement",
    "canva", "pdffiller", "dochub", "master pdf editor", "libreoffice draw",
]

_PDF_DATE = re.compile(r"D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz+\-])?(\d{2})?'?(\d{2})?'?")
_XMP_FIELD = r"<{tag}>([^<]+)</{tag}>|{tag}=\"([^\"]+)\""


def parse_pdf_date(s: str | None) -> datetime | None:
    if not s:
        return None
    m = _PDF_DATE.search(s)
    if not m:
        return None
    y, mo, d, h, mi, se, sign, th, tm = m.groups()
    try:
        dt = datetime(int(y), int(mo or 1), int(d or 1), int(h or 0), int(mi or 0), int(se or 0))
    except ValueError:
        return None
    off = timedelta(0)
    if sign in ("+", "-") and th:
        off = timedelta(hours=int(th), minutes=int(tm or 0)) * (1 if sign == "+" else -1)
    return dt.replace(tzinfo=timezone(off))


def _xmp(xml: str, tag: str) -> str | None:
    m = re.search(_XMP_FIELD.format(tag=re.escape(tag)), xml)
    return (m.group(1) or m.group(2)).strip() if m else None


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def count_revisions(data: bytes) -> int:
    """Number of incremental-update sections (linearized files carry one extra %%EOF)."""
    eofs = len(re.findall(rb"%%EOF", data))
    if b"/Linearized" in data[:2048]:
        eofs -= 1
    return max(eofs, 1)


class PdfMetadata:
    name = "pdf_metadata"

    def applies(self, ctx: DocumentContext) -> bool:
        return ctx.kind == "pdf"

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        out = DetectorOutput()
        meta = ctx.pdf.metadata or {}
        producer, creator = meta.get("producer") or "", meta.get("creator") or ""
        created, modified = parse_pdf_date(meta.get("creationDate")), parse_pdf_date(meta.get("modDate"))
        out.notes = {"producer": producer, "creator": creator,
                     "created": created.isoformat() if created else None,
                     "modified": modified.isoformat() if modified else None}

        def add(sev, conf, desc, **ev):
            out.findings.append(Finding(self.name, "metadata", sev, conf, desc, evidence=ev))

        tools = sorted({t for t in EDITOR_TOOLS if t in f"{producer} {creator}".lower()})
        if tools:
            add(0.45, 0.6, f"Document processed by editing software: {', '.join(tools)}",
                producer=producer, creator=creator)

        if created and modified:
            if modified < created - timedelta(minutes=1):
                add(0.55, 0.7, "Modification date precedes creation date", created=str(created), modified=str(modified))
            elif modified - created > timedelta(days=1):
                add(0.3, 0.5, f"Modified {(modified - created).days} days after creation",
                    created=str(created), modified=str(modified))
        elif not created and not modified:
            add(0.1, 0.4, "Creation and modification dates are missing (metadata stripped?)")

        revisions = count_revisions(ctx.data)
        out.notes["revisions"] = revisions
        if revisions > 1:
            add(min(0.35 + 0.1 * (revisions - 2), 0.7), 0.75,
                f"File contains {revisions - 1} incremental update(s) appended after the original save",
                revisions=revisions)

        xml = ctx.pdf.get_xml_metadata() or ""
        if xml:
            x_prod, x_tool = _xmp(xml, "pdf:Producer"), _xmp(xml, "xmp:CreatorTool")
            x_mod = _parse_iso(_xmp(xml, "xmp:ModifyDate"))
            if x_prod and producer and x_prod.strip().lower() != producer.strip().lower():
                add(0.4, 0.6, "Producer in XMP metadata differs from document info dictionary",
                    xmp_producer=x_prod, info_producer=producer)
            if x_mod and modified and abs((x_mod - modified).total_seconds()) > 120:
                add(0.35, 0.55, "XMP ModifyDate differs from info dictionary ModDate",
                    xmp_modified=str(x_mod), info_modified=str(modified))
            if x_tool:
                out.notes["xmp_creator_tool"] = x_tool
        return out
