# Project

Name: Veritas — Document Integrity Analyzer
Purpose: Score how likely it is that a document was tampered with. The output is a risk score in [0,1], the locations of suspicious regions, and an evidence list a person can read. It never gives a bare fake/real label.
Core Functionality: Upload a PDF, PNG or JPG. The system runs structure/metadata checks and visual/layout detectors, combines them into a risk score, and returns findings with bounding boxes and heatmaps. Uncertain cases go to a human review queue.
Technology Stack: React + Vite + TypeScript + Tailwind CSS + pdf.js (frontend); Python 3.11 + FastAPI + SQLAlchemy (backend); PyMuPDF, pdfminer.six, Pillow, OpenCV, NumPy (analysis); PaddleOCR (optional OCR); PostgreSQL; MinIO; Docker Compose.
Current State: MVP implemented and running in Docker. See ROADMAP.md and BLOCKERS.md.
