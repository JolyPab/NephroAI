"""Minimal raw-text lab parser (v1)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Dict, List, Optional


NOISE_PREFIXES = (
    "NUMERO DE SERVICIO",
    "PACIENTE",
    "GENERALES",
    "MEDICO",
    "FECHA",
    "IMP. DE RESULTADOS",
    "NUM. IMP",
    "PAG.",
)

TABLE_HEADERS = {"RESULTADOS", "UNIDADES", "VALORES DE", "NOTA", "VALORES DE REFERENCIA"}
SECTION_BANNED_KEYWORDS = (
    "LIMITE",
    "ALTO",
    "BAJO",
    "RIESGO",
    "ESTADIO",
    "NORMAL",
    "MODERADO",
)
VALUE_BANNED_KEYWORDS = ("RIESGO", "ESTADIO", "LIMITE")

REF_RANGE_RE = re.compile(
    r"(?P<min>\d+(?:[.,]\d+)*)\s*(?:a|to|\-|\u2013|\u2014)\s*(?P<max>\d+(?:[.,]\d+)*)",
    re.IGNORECASE,
)
RANGE_ONLY_RE = re.compile(
    r"^\s*\d+(?:[.,]\d+)?\s*a\s*\d+(?:[.,]\d+)?\s*$",
    re.IGNORECASE,
)
VALUE_UNIT_RE = re.compile(
    r"(?<!\S)(?P<value>(?:>=|<=|>|<)?\s*\d+(?:[.,]\d+)*)\s*(?P<unit>[A-Za-z%/\.0-9\^\-]+)"
)
UNIT_LIKE_RE = re.compile(r"(mg|mmol|mol|u/l|ui/l|ng/ml|%|x10\^|10\^|/ul|ml/min)", re.IGNORECASE)
DATE_LIKE_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}/\d{4}|\d{1,2}:\d{2})$",
    re.IGNORECASE,
)


def parse_raw_text(
    raw_text: str,
    default_date: Optional[date] = None,
    taken_at_source: str = "missing",
) -> List[Dict[str, Optional[object]]]:
    """Parse raw text into minimal lab records."""
    records: List[Dict[str, Optional[object]]] = []
    current_specimen: Optional[str] = None
    current_section: Optional[str] = None

    lines = _iter_clean_lines(raw_text)
    lines = _filter_band_rows(lines)
    lines = _stitch_multiline_records(lines)
    record_source = taken_at_source if default_date else "missing"
    for idx, line in enumerate(lines):
        normalized = _normalize_for_match(line)

        if _is_specimen_line(line, normalized):
            specimen = _extract_after_colon(line)
            if specimen:
                current_specimen = specimen
            continue

        if _should_update_section(line, normalized, lines, idx):
            current_section = line.strip()
            continue

        record = _parse_record_line(line, normalized, default_date, record_source)
        if not record:
            continue

        record["specimen"] = current_specimen
        record["section"] = current_section
        records.append(record)

    return records


def _iter_clean_lines(raw_text: str) -> List[str]:
    lines = []
    for raw in raw_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == ".":
            continue
        if re.fullmatch(r"[_\-\.\s\u2013\u2014]{3,}", line):
            continue

        normalized = _normalize_for_match(line)
        if not normalized:
            continue
        if normalized in TABLE_HEADERS:
            continue
        if normalized.startswith(NOISE_PREFIXES):
            continue

        lines.append(line)
    return lines


def _filter_band_rows(lines: List[str]) -> List[str]:
    filtered: List[str] = []
    i = 0
    skip_band_block = False

    while i < len(lines):
        line = lines[i]
        normalized = _normalize_for_match(line)

        if not skip_band_block:
            if _is_band_range_only(line):
                next_line = _next_significant_line(lines, i + 1)
                if next_line and _is_band_description(next_line):
                    skip_band_block = True
                    i += 1
                    continue
            filtered.append(line)
            i += 1
            continue

        if _is_band_range_only(line) or _is_band_description(line):
            i += 1
            continue
        if _looks_like_test_line(line, normalized) or _looks_like_inline_record(line):
            skip_band_block = False
            continue

        i += 1

    return filtered


def _stitch_multiline_records(lines: List[str]) -> List[str]:
    stitched: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        normalized = _normalize_for_match(line)

        if _is_specimen_line(line, normalized):
            stitched.append(line)
            i += 1
            continue

        if _looks_like_inline_record(line):
            stitched.append(line)
            i += 1
            continue

        if _looks_like_test_line(line, normalized) and i + 2 < len(lines):
            value_line = lines[i + 1]
            unit_line = lines[i + 2]
            if _is_value_line(value_line) and _is_unit_line(unit_line):
                ref_line = lines[i + 3] if i + 3 < len(lines) else None
                if ref_line and _is_ref_line(ref_line):
                    stitched.append(f"{line} {value_line} {unit_line} {ref_line}")
                    i += 4
                else:
                    stitched.append(f"{line} {value_line} {unit_line}")
                    i += 3
                continue

        stitched.append(line)
        i += 1

    return stitched


def _normalize_for_match(text: str) -> str:
    text = _strip_accents(text)
    text = re.sub(r"\s+", " ", text).strip().upper()
    text = re.sub(r"[^A-Z0-9:/. ]", "", text)
    return text


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _is_specimen_line(line: str, normalized: str) -> bool:
    if ":" not in line:
        return False
    return "MUESTRA" in normalized and "ANAL" in normalized


def _extract_after_colon(line: str) -> Optional[str]:
    if ":" not in line:
        return None
    value = line.split(":", 1)[1].strip()
    return value or None


def _looks_like_section(line: str, normalized: str) -> bool:
    length = len(line.strip())
    if length < 8 or length > 60:
        return False
    if " " not in line.strip():
        return False
    if line.strip().endswith("."):
        return False
    if any(ch.isdigit() for ch in line):
        return False
    if ":" in line:
        return False
    if line != line.upper():
        return False
    if normalized in TABLE_HEADERS:
        return False
    if any(keyword in normalized for keyword in SECTION_BANNED_KEYWORDS):
        return False
    return True


def _should_update_section(
    line: str,
    normalized: str,
    lines: List[str],
    idx: int,
) -> bool:
    if not _looks_like_section(line, normalized):
        return False
    if _is_section_header_noise(line, normalized):
        return False
    if _looks_like_person_name(line):
        return False
    if _has_upcoming_record_with_prefix(lines, idx, line):
        return False

    next_line = _next_significant_line(lines, idx + 1)
    if next_line:
        if _looks_like_test_line(line, normalized) and _is_value_line(next_line):
            return False
        if _looks_like_inline_record(next_line):
            return False
        if _is_demographic_line(next_line):
            return False
    return True


def _is_section_header_noise(line: str, normalized: str) -> bool:
    if ":" in line:
        return True
    if normalized.startswith(NOISE_PREFIXES):
        return True
    if normalized.startswith("PAG."):
        return True
    if any(keyword in normalized for keyword in ("FECHA", "NUMERO", "PACIENTE", "MEDICO", "IMP")):
        return True
    return False


def _looks_like_person_name(line: str) -> bool:
    tokens = [token.strip(".") for token in line.split() if token.strip(".")]
    if not tokens:
        return False
    if any(len(token) == 1 for token in tokens):
        return True
    return False


def _is_demographic_line(line: str) -> bool:
    normalized = _normalize_for_match(line)
    if not normalized:
        return False
    if "ANOS" in normalized or "ANOS," in normalized:
        return True
    if "MASCULINO" in normalized or "FEMENINO" in normalized:
        return True
    if DATE_LIKE_RE.match(line.strip()):
        return True
    if "HRS" in normalized:
        return True
    return False


def _next_significant_line(lines: List[str], start_index: int) -> Optional[str]:
    for idx in range(start_index, min(start_index + 6, len(lines))):
        line = lines[idx]
        normalized = _normalize_for_match(line)
        if not normalized:
            continue
        if normalized in TABLE_HEADERS or normalized.startswith(NOISE_PREFIXES):
            continue
        if _is_specimen_line(line, normalized):
            continue
        if normalized.startswith("METODO") or normalized.startswith("ANALITOS"):
            continue
        if line.strip().startswith("."):
            continue
        return line
    return None


def _has_upcoming_record_with_prefix(
    lines: List[str],
    start_index: int,
    prefix: str,
) -> bool:
    prefix_norm = _normalize_for_match(prefix)
    if not prefix_norm:
        return False
    for idx in range(start_index + 1, min(start_index + 15, len(lines))):
        line = lines[idx]
        if not re.search(r"\d", line):
            continue
        candidate_norm = _normalize_for_match(line)
        if candidate_norm.startswith(prefix_norm):
            return True
    return False


def _looks_like_inline_record(line: str) -> bool:
    _, _, line_wo_ref = _extract_ref_range(line)
    return bool(_extract_numeric_value(line_wo_ref) or _extract_categorical_value(line_wo_ref))


def _looks_like_test_line(line: str, normalized: str) -> bool:
    if not normalized or len(normalized) < 2:
        return False
    if any(ch.isdigit() for ch in line):
        return False
    if ":" in line:
        return False
    if normalized in TABLE_HEADERS:
        return False
    if _is_unit_line(line):
        return False
    return True


def _parse_record_line(
    line: str,
    normalized: str,
    default_date: Optional[date],
    taken_at_source: str,
) -> Optional[Dict[str, Optional[object]]]:
    ref_min, ref_max, line_wo_ref = _extract_ref_range(line)

    numeric = _extract_numeric_value(line_wo_ref)
    if numeric:
        value_raw, unit_raw, start_index = numeric
        if not _is_unit_valid(unit_raw):
            return None
        value_operator, value_num = _parse_numeric_value(value_raw)
        if value_num is None:
            return None
        test_name_raw = line[:start_index].strip()
        if not test_name_raw or test_name_raw.strip().lower() == "x":
            return None
        if not (_is_unit_like(unit_raw) or ref_min is not None):
            return None
        record = _build_record(
            test_name_raw=test_name_raw,
            value_type="numeric",
            value_num=value_num,
            value_cat=None,
            value_operator=value_operator,
            unit_raw=unit_raw,
            ref_min=ref_min,
            ref_max=ref_max,
            taken_at=default_date,
            taken_at_source=taken_at_source,
        )
        stage = _derive_egfr_stage(test_name_raw, record.get("unit_norm"), value_num)
        if stage:
            record["derived_stage"] = stage
        return record

    categorical = _extract_categorical_value(line_wo_ref)
    if categorical:
        value_raw, unit_raw, start_index = categorical
        if not _is_unit_valid(unit_raw):
            return None
        test_name_raw = line[:start_index].strip()
        if not test_name_raw or test_name_raw.strip().lower() == "x":
            return None
        if not (_is_unit_like(unit_raw) or ref_min is not None):
            return None
        return _build_record(
            test_name_raw=test_name_raw,
            value_type="categorical",
            value_num=None,
            value_cat=value_raw,
            value_operator=None,
            unit_raw=unit_raw,
            ref_min=ref_min,
            ref_max=ref_max,
            taken_at=default_date,
            taken_at_source=taken_at_source,
        )

    return None


def _extract_ref_range(line: str) -> tuple[Optional[float], Optional[float], str]:
    match = REF_RANGE_RE.search(line)
    if not match:
        return None, None, line
    ref_min = parse_number(match.group("min"))
    ref_max = parse_number(match.group("max"))
    line_wo_ref = (line[:match.start()] + " " + line[match.end():]).strip()
    return ref_min, ref_max, line_wo_ref


def _is_value_line(line: str) -> bool:
    return _is_numeric_line(line) or _is_categorical_line(line)


def _is_numeric_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.search(r"[A-Za-z]", stripped):
        return False
    if not re.search(r"\d", stripped):
        return False
    if not re.fullmatch(r"(?:[<>]=?)?\s*[\d.,]+", stripped):
        return False
    candidate = re.sub(r"^[<>]=?", "", stripped).strip()
    return parse_number(candidate) is not None


def _is_categorical_line(line: str) -> bool:
    if re.search(r"\d", line):
        return False
    if ":" in line:
        return False
    normalized = _normalize_for_match(line)
    if not normalized:
        return False
    if any(keyword in normalized for keyword in VALUE_BANNED_KEYWORDS):
        return False
    if _looks_like_section(line, normalized):
        return False
    if normalized in TABLE_HEADERS:
        return False
    if normalized.startswith(NOISE_PREFIXES):
        return False
    if _is_unit_line(line):
        return False
    return True


def _is_unit_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if not re.fullmatch(r"[A-Za-z0-9%/\.\\^\\-]+", stripped):
        return False
    if DATE_LIKE_RE.match(stripped):
        return False
    return _is_unit_like(stripped)


def _is_ref_line(line: str) -> bool:
    return bool(REF_RANGE_RE.search(line))


def _extract_numeric_value(line: str) -> Optional[tuple[str, str, int]]:
    for match in VALUE_UNIT_RE.finditer(line):
        value_raw = match.group("value").strip()
        unit_raw = match.group("unit").strip()
        if not _is_unit_valid(unit_raw):
            continue
        return value_raw, unit_raw, match.start()
    return None


def _extract_categorical_value(line: str) -> Optional[tuple[str, str, int]]:
    tokens = line.split()
    if len(tokens) < 3:
        return None

    for idx in range(len(tokens) - 1, 0, -1):
        unit_raw = tokens[idx].strip()
        if not _is_unit_valid(unit_raw) or not _is_unit_like(unit_raw):
            continue
        value_raw = tokens[idx - 1].strip()
        if re.search(r"\d", value_raw):
            continue
        marker = f"{value_raw} {unit_raw}"
        start_index = line.rfind(marker)
        if start_index == -1:
            start_index = line.rfind(value_raw)
        return value_raw, unit_raw, start_index
    return None


def _is_unit_valid(unit_raw: str) -> bool:
    if not unit_raw:
        return False
    if DATE_LIKE_RE.match(unit_raw):
        return False
    if unit_raw.upper().startswith("HRS"):
        return False
    return True


def _is_unit_like(unit_raw: str) -> bool:
    return bool(UNIT_LIKE_RE.search(unit_raw))


def _is_band_range_only(line: str) -> bool:
    return bool(RANGE_ONLY_RE.match(line))


def _is_band_description(line: str) -> bool:
    normalized = _normalize_for_match(line)
    if not normalized:
        return False
    return "ESTADIO" in normalized or "TFG" in normalized or "EGFR" in normalized or "GFR" in normalized


def _derive_egfr_stage(
    test_name_raw: str,
    unit_norm: Optional[str],
    value_num: Optional[float],
) -> Optional[str]:
    if value_num is None:
        return None
    if not unit_norm or "ML/MIN/1.73" not in unit_norm.upper():
        return None
    name_norm = _normalize_for_match(test_name_raw)
    if not any(keyword in name_norm for keyword in ("TFG", "EGFR", "GFR", "FILTRACION")):
        return None

    if value_num >= 90:
        return "G1"
    if value_num >= 60:
        return "G2"
    if value_num >= 45:
        return "G3A"
    if value_num >= 30:
        return "G3B"
    if value_num >= 15:
        return "G4"
    return "G5"


def _parse_numeric_value(value_raw: str) -> tuple[Optional[str], Optional[float]]:
    value_raw = value_raw.strip()
    op = None
    if value_raw.startswith(">="):
        op = ">="
        value_raw = value_raw[2:].strip()
    elif value_raw.startswith("<="):
        op = "<="
        value_raw = value_raw[2:].strip()
    elif value_raw.startswith(">"):
        op = ">"
        value_raw = value_raw[1:].strip()
    elif value_raw.startswith("<"):
        op = "<"
        value_raw = value_raw[1:].strip()

    value_num = parse_number(value_raw)
    return op, value_num


def parse_number(raw: str) -> Optional[float]:
    if raw is None:
        return None
    value = raw.strip().replace(" ", "")
    if not value:
        return None

    if "," in value and "." in value:
        value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        if len(parts[-1]) == 3 and all(part.isdigit() for part in parts):
            value = "".join(parts)
        else:
            value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


def _build_record(
    test_name_raw: str,
    value_type: str,
    value_num: Optional[float],
    value_cat: Optional[str],
    value_operator: Optional[str],
    unit_raw: Optional[str],
    ref_min: Optional[float],
    ref_max: Optional[float],
    taken_at: Optional[date],
    taken_at_source: str,
) -> Dict[str, Optional[object]]:
    unit_norm = unit_raw.upper() if unit_raw else None
    return {
        "test_name_raw": test_name_raw,
        "value_type": value_type,
        "value_num": value_num,
        "value_cat": value_cat,
        "value_operator": value_operator,
        "unit_raw": unit_raw,
        "unit_norm": unit_norm,
        "ref_min": ref_min,
        "ref_max": ref_max,
        "specimen": None,
        "section": None,
        "taken_at": taken_at,
        "taken_at_source": taken_at_source,
    }
