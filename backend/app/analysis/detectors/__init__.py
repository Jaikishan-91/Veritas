"""Detector registry. To add a detector: implement `Detector` in a module and append it to `all_detectors`."""
from __future__ import annotations

from typing import Protocol

from ..types import DetectorOutput, DocumentContext


class Detector(Protocol):
    name: str

    def applies(self, ctx: DocumentContext) -> bool: ...

    def run(self, ctx: DocumentContext) -> DetectorOutput: ...


def all_detectors() -> list[Detector]:
    from .copy_move import CopyMove
    from .ela import ErrorLevelAnalysis
    from .font_consistency import FontConsistency
    from .image_metadata import ImageMetadata
    from .noise import NoiseInconsistency
    from .ocr_text import OcrText
    from .pdf_metadata import PdfMetadata
    from .pdf_structure import PdfStructure

    return [
        PdfMetadata(), PdfStructure(), FontConsistency(), ImageMetadata(),
        ErrorLevelAnalysis(), NoiseInconsistency(), CopyMove(), OcrText(),
    ]
