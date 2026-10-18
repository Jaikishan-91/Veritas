# Constraints
Hard Constraints:
- Stack fixed by user: React/Tailwind/pdf.js, Python/FastAPI, PaddleOCR, PostgreSQL, MinIO, PyMuPDF, pdfminer.six; Docker.
- MVP formats: PDF, PNG, JPG only.
- Output is a probabilistic risk score with evidence, never a binary verdict.
- The detectors are heuristics, not trained models. Scores are uncalibrated until a labelled dataset exists (see ROADMAP).
Budget: Local/Docker deployment, no paid services.
