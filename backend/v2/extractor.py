from __future__ import annotations

from backend.v2.llm_client import extract_import_v2_from_pdf_bytes
from backend.v2.schemas import ImportV2


def _use_raw_names_as_analyte_keys(payload: ImportV2) -> ImportV2:
    for metric in payload.metrics:
        raw_name = (metric.raw_name or "").strip()
        if raw_name:
            metric.analyte_key = raw_name
    return payload


def _normalize_scientific_units(payload: ImportV2) -> ImportV2:
    for metric in payload.metrics:
        unit = metric.unit
        if unit is None:
            continue
        value = metric.value_numeric
        if value is None:
            continue
        if not unit.startswith("x10^"):
            continue
        parts = unit.split("^", 1)
        if len(parts) != 2:
            continue
        after = parts[1]
        digits = []
        for ch in after:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        if not digits:
            continue
        n = int("".join(digits))
        if value < 1000:
            continue
        reference = metric.reference
        if reference is None or reference.max is None:
            continue
        if reference.max >= 1000:
            continue
        metric.value_numeric = round(value / (10**n), 6)
    return payload


async def extract(pdf_bytes: bytes) -> ImportV2:
    raw_dict = await extract_import_v2_from_pdf_bytes(pdf_bytes)
    payload = ImportV2.model_validate(raw_dict)
    payload = _use_raw_names_as_analyte_keys(payload)
    payload = _normalize_scientific_units(payload)
    return payload
