"""PDF text extraction (text layer + OCR fallback)."""

from __future__ import annotations

import io
from typing import Dict, List

import fitz  # PyMuPDF
import pdfplumber

from backend.vision_parser import select_pages_for_vision, ocr_pages_to_text


class NoTextLayerError(Exception):
    """Raised when a PDF has no extractable text."""


def _extract_pages_text(pdf_bytes: bytes) -> List[Dict[str, str]]:
    if not pdf_bytes or len(pdf_bytes) < 100:
        raise ValueError("Empty or invalid PDF file")

    pages: List[Dict[str, str]] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Invalid PDF: {exc}") from exc

    try:
        for page_index, page in enumerate(doc):
            pages.append({"page": page_index, "text": page.get_text("text") or ""})
    finally:
        doc.close()

    if any(page["text"].strip() for page in pages):
        return pages

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page_index, page in enumerate(pdf.pages):
                pages.append({"page": page_index, "text": page.extract_text() or ""})
    except Exception:
        return pages

    return pages


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF without OCR fallback."""
    pages = _extract_pages_text(pdf_bytes)
    text = "\n".join(page["text"] for page in pages if page["text"])
    if not text.strip():
        raise NoTextLayerError("No text layer found in PDF. PDF appears to be image-based.")
    return text


def extract_raw_text(pdf_bytes: bytes) -> str:
    """Return raw text using text layer, with OCR fallback for image-based pages."""
    pages = _extract_pages_text(pdf_bytes)
    if not pages:
        raise ValueError("PDF has no pages")

    page_text = {page["page"]: (page["text"] or "") for page in pages}
    has_text = any(text.strip() for text in page_text.values())

    ocr_pages = select_pages_for_vision(pdf_bytes)
    if not has_text and not ocr_pages:
        ocr_pages = sorted(page_text.keys())

    if ocr_pages:
        try:
            ocr_results = ocr_pages_to_text(pdf_bytes, ocr_pages)
        except Exception:
            if not has_text:
                raise
        else:
            for result in ocr_results:
                page_index = int(result.get("page", 0))
                page_text[page_index] = result.get("text", "") or ""

    raw_text = "\n\n".join(
        page_text[page_index].strip()
        for page_index in sorted(page_text.keys())
        if page_text[page_index].strip()
    )
    if not raw_text:
        raise NoTextLayerError("No text could be extracted from PDF.")
    return raw_text
