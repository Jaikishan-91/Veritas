"""Per-line font family / size / baseline / colour anomalies and subset-tag inconsistencies in PDFs."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from ..types import DetectorOutput, DocumentContext, Finding, norm_bbox

_SUBSET = re.compile(r"^[A-Z]{6}\+")
MIN_STYLE_LINES, MIN_STYLE_SHARE = 3, 0.15
_STYLE = re.compile(r"[-,]?(bold|italic|oblique|regular|medium|light|semibold|black|mt|ps|it|bd)+$", re.I)


def family(font: str) -> str:
    f = _SUBSET.sub("", font)
    f = re.split(r"[-,]", f)[0] if re.search(r"[-,]", f) else f
    return _STYLE.sub("", f).lower()


def visual_lines(page) -> list[list[dict]]:
    """Group spans by shared baseline and horizontal proximity, regardless of how the PDF structures them.

    Inserted text is usually a separate text object, so PyMuPDF's own lines would never compare it to its neighbours.
    """
    spans = [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]
             if s["text"].strip() and l["dir"] == (1.0, 0.0)]
    spans.sort(key=lambda s: (s["origin"][1], s["bbox"][0]))
    lines: list[list[dict]] = []
    for s in spans:
        for line in lines:
            ref = line[0]
            if (abs(s["origin"][1] - ref["origin"][1]) < 0.3 * max(ref["size"], s["size"])
                    and s["bbox"][0] < max(x["bbox"][2] for x in line) + 3 * ref["size"]):
                line.append(s)
                break
        else:
            lines.append([s])
    return lines


def style(s: dict) -> tuple:
    return family(s["font"]), round(s["size"] * 2) / 2, s["color"]


def established_styles(lines: list[list[dict]]) -> set[tuple]:
    """Styles that are part of the page design: used on several lines or for a sizeable share of the text.

    Headings, form labels, captions and accent fonts recur; a retyped field is usually a one-off. Only spans whose
    style is *not* established can be reported as font/size/colour mismatches.
    """
    line_count: Counter = Counter()
    chars: Counter = Counter()
    for line in lines:
        seen = set()
        for s in line:
            st = style(s)
            chars[st] += len(s["text"].strip())
            seen.add(st)
        line_count.update(seen)
    total = sum(chars.values()) or 1
    return {st for st in chars if line_count[st] >= MIN_STYLE_LINES or chars[st] / total >= MIN_STYLE_SHARE}


class FontConsistency:
    name = "font_consistency"

    def applies(self, ctx: DocumentContext) -> bool:
        return ctx.kind == "pdf"

    def run(self, ctx: DocumentContext) -> DetectorOutput:
        out = DetectorOutput()
        for pno in range(len(ctx.pages)):
            page = ctx.pdf[pno]
            w, h = page.rect.width, page.rect.height
            self._subsets(page, pno, out)
            lines = visual_lines(page)
            established = established_styles(lines)
            for line in lines:
                self._line(line, established, pno, w, h, out)
        return out

    def _subsets(self, page, pno, out):
        tags = defaultdict(set)
        for f in page.get_fonts():
            base = f[3]
            if _SUBSET.match(base):
                tags[_SUBSET.sub("", base)].add(base[:6])
        multi = {k: sorted(v) for k, v in tags.items() if len(v) > 1}
        if multi:
            out.findings.append(Finding(
                "font_consistency", "font_mismatch", 0.4, 0.55,
                "Same font embedded as multiple separate subsets on one page (text likely added by a different tool/session)",
                page=pno, evidence={"fonts": multi}))

    def _line(self, spans, established, pno, w, h, out):
        if len(spans) < 2:
            return
        chars = Counter()
        sizes = Counter()
        colors = Counter()
        for s in spans:
            n = len(s["text"].strip())
            chars[family(s["font"])] += n
            sizes[round(s["size"], 1)] += n
            colors[s["color"]] += n
        total = sum(chars.values())
        if total < 6:
            return
        dom_font, dom_size, dom_color = chars.most_common(1)[0][0], sizes.most_common(1)[0][0], colors.most_common(1)[0][0]
        ref = [s for s in spans if round(s["size"], 1) == dom_size]
        base_y = sorted(s["origin"][1] for s in ref)[len(ref) // 2]
        line_text = " ".join(s["text"] for s in sorted(spans, key=lambda s: s["bbox"][0]))[:200]
        for s in spans:
            text = s["text"].strip()
            reasons, sev = [], 0.0
            has_digit = any(c.isdigit() for c in text)
            design = style(s) in established
            if not design and family(s["font"]) != dom_font and len(text) <= 0.5 * total:
                reasons.append(f"font '{s['font']}' differs from line font '{dom_font}'")
                sev = max(sev, 0.55 if has_digit else 0.45)
            size_ratio = s["size"] / dom_size if dom_size else 1
            raised = s["origin"][1] < base_y - 0.2 * dom_size
            if not design and abs(size_ratio - 1) > 0.12 and not (size_ratio < 0.85 and raised):  # skip superscripts
                reasons.append(f"size {s['size']:.1f} vs line {dom_size}")
                sev = max(sev, 0.35)
            elif abs(size_ratio - 1) <= 0.05 and abs(s["origin"][1] - base_y) > 0.12 * dom_size:
                reasons.append(f"baseline offset {s['origin'][1] - base_y:+.1f}pt")
                sev = max(sev, 0.4)
            if not design and s["color"] != dom_color and _near(s["color"], dom_color):
                reasons.append(f"colour #{s['color']:06x} nearly matches line colour #{dom_color:06x}")
                sev = max(sev, 0.35)
            if reasons:
                out.findings.append(Finding(
                    "font_consistency", "font_mismatch", sev, 0.55,
                    f"Span '{text[:40]}' inconsistent with its line: " + "; ".join(reasons),
                    page=pno, bbox=norm_bbox(*s["bbox"], w, h),
                    evidence={"span_text": text[:200], "line_text": line_text, "span_font": s["font"],
                              "span_size": round(s["size"], 2), "line_font": dom_font, "line_size": dom_size}))


def _near(a: int, b: int, tol: int = 24) -> bool:
    ca = [(a >> k) & 255 for k in (16, 8, 0)]
    cb = [(b >> k) & 255 for k in (16, 8, 0)]
    return max(abs(x - y) for x, y in zip(ca, cb)) <= tol
