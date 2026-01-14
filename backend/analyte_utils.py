"""Helpers for analyte name normalization and keys."""

import re
import unicodedata
from typing import Optional


def normalize_analyte_name(name: Optional[str]) -> str:
    """
    Normalize analyte names for stable grouping and comparisons.

    - Trim and collapse whitespace
    - Uppercase
    - Remove diacritics
    - Normalize spacing around slashes
    """
    if not name:
        return ""

    text = str(name).replace("\u00a0", " ").strip()
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    text = text.upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s*/\s*", "/", text)
    text = text.rstrip(":").strip()

    return text


def analyte_key(
    name: Optional[str],
    value: Optional[float],
    value_text: Optional[str],
    unit: Optional[str],
    material: Optional[str],
    taken_at_iso: Optional[str],
) -> tuple:
    """Build a stable dedupe key for analyte rows."""
    value_key = value if value is not None else (value_text or "").strip().upper()
    unit_key = (unit or "").strip().upper()
    material_key = (material or "").strip().upper()
    return (
        normalize_analyte_name(name),
        value_key,
        unit_key,
        material_key,
        taken_at_iso or "",
    )
