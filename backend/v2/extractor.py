from __future__ import annotations

import re
import unicodedata

from backend.v2.llm_client import extract_import_v2_from_pdf_bytes
from backend.v2.schemas import ImportV2


def _normalize_key_chunk(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def _assign_series_keys(payload: ImportV2) -> ImportV2:
    for metric in payload.metrics:
        raw_chunk = _normalize_key_chunk(metric.raw_name or "")
        specimen_chunk = _normalize_key_chunk(
            metric.specimen.value if hasattr(metric.specimen, "value") else str(metric.specimen)
        )
        value_kind = "NUM" if metric.value_numeric is not None else "TEXT"
        if raw_chunk and specimen_chunk:
            metric.analyte_key = f"{raw_chunk}__{specimen_chunk}__{value_kind}"
        elif raw_chunk:
            metric.analyte_key = f"{raw_chunk}__{value_kind}"
        elif specimen_chunk:
            metric.analyte_key = f"UNKNOWN__{specimen_chunk}__{value_kind}"
        else:
            metric.analyte_key = f"UNKNOWN__{value_kind}"
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
    payload = _assign_series_keys(payload)
    payload = _normalize_scientific_units(payload)
    return payload
