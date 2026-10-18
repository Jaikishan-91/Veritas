# Requirements

## Functional (MVP)
- FR1 Upload PDF, PNG and JPG/JPEG files (max 25 MB by default) and get a document id.
- FR2 Analysis runs asynchronously. Status values: `queued -> processing -> completed | failed`.
- FR3 Output: `risk_score` in [0,1], `risk_band` (low/medium/high), `needs_review` flag, and a list of findings.
- FR4 Each finding has: detector, category, severity [0,1], confidence [0,1], page, normalized bbox (optional), human-readable description, and a structured evidence dict.
- FR5 Categories covered: `text_tampering`, `copy_move`, `splicing`, `font_mismatch`, `metadata`, `structure`.
- FR6 Heatmap artifacts (ELA, noise residual) are stored and viewable as overlays.
- FR7 Uncertain cases are routed to a review queue: score in the uncertainty band, or detector failure or low coverage. Reviewers record a decision (`authentic|tampered|inconclusive`) and notes.
- FR8 UI: upload page, document viewer (pdf.js / image) with bbox and heatmap overlays plus the evidence list, and a review queue.
- FR9 Detection must still produce useful signal after format conversion or flattening. Visual detectors run on the rendered raster of every input, not only on PDF internals.

## Non-Functional
- NFR1 Explainability: every contribution to the score can be traced to a finding.
- NFR2 Deterministic for the same input and config.
- NFR3 Pluggable detectors: adding one should mean one module plus a registry entry.
- NFR4 Optional heavy dependencies (PaddleOCR) are allowed to be missing. The affected detector is skipped and the gap is reported as reduced coverage.
- NFR5 Uploads are validated by magic bytes, not by extension, with size limits enforced.

## Post-MVP
- Office formats (python-docx/openpyxl), larger datasets and calibration, digital-signature validation, explainability that has been validated against data.
