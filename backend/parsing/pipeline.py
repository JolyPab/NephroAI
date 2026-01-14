"""Parsing pipeline helpers with OCR fallback."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Callable, Dict, List, Optional

import fitz  # PyMuPDF

from backend.parsing.lab_parser_v0 import parse_raw_text



def coerce_raw_text(raw_text: Any) -> str:
    if isinstance(raw_text, str):
        return raw_text
    if isinstance(raw_text, bytes):
        return raw_text.decode("utf-8", errors="ignore")
    return str(raw_text)


def compute_parse_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    names = []
    for record in records:
        name = (record.get("test_name_raw") or "").strip()
        if not name:
            continue
        names.append(" ".join(name.split()).upper())
    unique_names = set(names)
    return {
        "records_count": len(records),
        "unique_tests_count": len(unique_names),
        "has_creatinina": any("CREATININA" in name for name in unique_names),
    }


def parse_with_ocr_fallback(
    pdf_bytes: bytes,
    raw_text: Any,
    parse_func: Callable[[str, Optional[date], str], List[Dict[str, Any]]] = parse_raw_text,
    select_pages_func: Optional[Callable[[bytes], List[int]]] = None,
    ocr_func: Optional[Callable[[bytes, List[int]], List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    raw_text = coerce_raw_text(raw_text)
    report_date, report_source = extract_report_date(raw_text)
    records = parse_func(
        raw_text,
        default_date=report_date,
        taken_at_source=report_source,
    )
    metrics_before = compute_parse_metrics(records)
    trigger = _should_trigger_ocr(metrics_before, len(raw_text))

    ocr_text = ""
    ocr_error: Optional[str] = None
    metrics_after = metrics_before

    if trigger:
        if select_pages_func is None or ocr_func is None:
            select_pages_func, ocr_func = _load_ocr_funcs()
        try:
            ocr_text = _collect_ocr_text(pdf_bytes, select_pages_func, ocr_func)
        except Exception as exc:
            ocr_error = str(exc)

        if ocr_text:
            merged_text = f"{raw_text}\n{ocr_text}" if raw_text else ocr_text
            ocr_date, ocr_source = extract_report_date(ocr_text)
            report_date, report_source = _pick_report_date(
                report_date,
                report_source,
                ocr_date,
                ocr_source,
            )
            records = parse_func(
                merged_text,
                default_date=report_date,
                taken_at_source=report_source,
            )
            metrics_after = compute_parse_metrics(records)

    return {
        "raw_text": raw_text,
        "records": records,
        "metrics": metrics_after,
        "metrics_before": metrics_before,
        "triggered_by": trigger,
        "ocr_text": ocr_text,
        "ocr_error": ocr_error,
    }


def _should_trigger_ocr(metrics: Dict[str, Any], raw_text_len: int) -> Optional[str]:
    if metrics.get("records_count", 0) == 0:
        return "records_zero"
    if metrics.get("records_count", 0) < 3 and raw_text_len < 5000:
        return "few_records_short_text"
    return None


def _collect_ocr_text(
    pdf_bytes: bytes,
    select_pages_func: Callable[[bytes], List[int]],
    ocr_func: Callable[[bytes, List[int]], List[Dict[str, Any]]],
) -> str:
    pages = select_pages_func(pdf_bytes)
    if not pages:
        pages = _all_page_indices(pdf_bytes)

    ocr_pages = ocr_func(pdf_bytes, pages)
    return "\n\n".join(
        page.get("text", "") for page in ocr_pages if page.get("text")
    )


def _all_page_indices(pdf_bytes: bytes) -> List[int]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return list(range(len(doc)))
    finally:
        doc.close()


def extract_report_date(raw_text: str) -> tuple[Optional[date], str]:
    """Extract report date from raw text (FECHA DE TOMA/MUESTRA/REGISTRO/LIBERACION)."""
    if not raw_text:
        return None, "missing"

    patterns = [
        ("toma", r"FECHA\s+DE\s+(?:TOMA|MUESTRA)\s*:?\s*([0-3]?\d/[0-1]?\d/\d{4})"),
        ("registro", r"FECHA\s+DE\s+REGISTRO\s*:?\s*([0-3]?\d/[0-1]?\d/\d{4})"),
        ("liberacion", r"FECHA\s+DE\s+LIBERACION\s*:?\s*([0-3]?\d/[0-1]?\d/\d{4})"),
    ]

    for source, pattern in patterns:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            continue
        parsed = _parse_ddmmyyyy(match.group(1))
        if parsed:
            return parsed, source

    return None, "missing"


def _parse_ddmmyyyy(value: str) -> Optional[date]:
    parts = value.split("/")
    if len(parts) != 3:
        return None
    try:
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        return date(year, month, day)
    except ValueError:
        return None


def _pick_report_date(
    current_date: Optional[date],
    current_source: str,
    candidate_date: Optional[date],
    candidate_source: str,
) -> tuple[Optional[date], str]:
    priority = {"toma": 0, "registro": 1, "liberacion": 2, "missing": 3}
    if candidate_date is None:
        return current_date, current_source
    if current_date is None:
        return candidate_date, candidate_source
    if priority.get(candidate_source, 3) < priority.get(current_source, 3):
        return candidate_date, candidate_source
    return current_date, current_source


def _load_ocr_funcs() -> tuple[
    Callable[[bytes], List[int]],
    Callable[[bytes, List[int]], List[Dict[str, Any]]],
]:
    from backend.vision_parser import select_pages_for_vision, ocr_pages_to_text
    return select_pages_for_vision, ocr_pages_to_text
