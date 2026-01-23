"""Context-aware parsing helpers for lab text extraction."""

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple, Union

from analyte_utils import normalize_analyte_name


_CATEGORICAL_VALUES = {
    "NEGATIVO",
    "POSITIVO",
    "NORMAL",
    "ANORMAL",
    "CLARO",
    "AMARILLO",
    "TRAZA",
    "TRAZAS",
    "PRESENTE",
    "AUSENTE",
    "TURBIO",
    "LIGERAMENTE",
}

_SPECIMEN_KEYWORDS = [
    "SUERO",
    "ORINA 24 HRS",
    "ORINA 24HRS",
    "ORINA",
    "SANGRE",
    "PLASMA",
    "HECES",
    "SALIVA",
]

_UNIT_TOKEN_RE = re.compile(r"[A-Za-z/%\^0-9\.\-]+")
_SECTION_HINTS = {
    "PERFIL",
    "PANEL",
    "EXAMEN",
    "EXAMENES",
    "PRUEBA",
    "PRUEBAS",
    "ESTUDIO",
    "BIOQUIMICA",
    "HEMATOLOGIA",
    "MICROBIOLOGIA",
    "SEROLOGIA",
    "INMUNOLOGIA",
    "BACTERIOLOGIA",
    "COAGULACION",
}


@dataclass
class ReferenceParsed:
    type: str
    min: Optional[float] = None
    max: Optional[float] = None
    bands: Optional[List[Dict[str, Optional[str]]]] = None


@dataclass
class ParsedRecord:
    page: int
    section_path: List[str]
    specimen: Optional[str]
    method: Optional[str]
    test_name_raw: str
    test_name_norm: str
    value_type: str
    value_num: Optional[float]
    value_cat: Optional[str]
    unit_raw: Optional[str]
    unit_norm: Optional[str]
    ref_raw: Optional[str]
    ref_parsed: Optional[ReferenceParsed]
    raw_fragment: str
    series_key: str


def normalize_text(text: str) -> List[str]:
    """Normalize raw text into clean non-empty lines."""
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00d7", "x").replace("\u00b5", "u")
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"[_\-\.]{3,}", " ", line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if re.fullmatch(r"[_\-\.\s]{3,}", line):
            continue
        lines.append(line)
    return lines


def _normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    unit = unit.replace("\u00d7", "x").replace("\u00b5", "u")
    unit = unit.strip()
    unit = re.sub(r"\s+", " ", unit)
    unit = unit.rstrip(":")
    return unit.upper() if unit else None


def _strip_diacritics(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def parse_number(value: str) -> Optional[float]:
    """Parse a number with thousands/decimal separators."""
    if value is None:
        return None
    s = str(value).strip().replace(" ", "")
    if not s:
        return None
    s = s.replace("\u2212", "-")

    if "," in s and "." in s:
        s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    if "," in s:
        parts = s.split(",")
        if len(parts[-1]) == 3:
            s = "".join(parts)
        else:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    try:
        return float(s)
    except ValueError:
        return None


def _parse_band_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    line = line.strip()
    if not line:
        return None

    # Range with label: "100 a 200 Bajo Riesgo"
    range_match = re.search(
        r"([+-]?\d[\d.,]*)\s*(?:a|to|\u2013|-|\u2014)\s*([+-]?\d[\d.,]*)",
        line,
        flags=re.IGNORECASE,
    )
    if range_match:
        min_val = parse_number(range_match.group(1))
        max_val = parse_number(range_match.group(2))
        label = line[range_match.end():].strip() or None
        return {"min": min_val, "max": max_val, "op": None, "label": label}

    # Min/max only: "< 130 Optimo" / "> 160 Alto"
    op_match = re.search(r"([<>])\s*([+-]?\d[\d.,]*)", line)
    if op_match:
        op = op_match.group(1)
        num = parse_number(op_match.group(2))
        label = line[op_match.end():].strip() or None
        return {
            "min": num if op == ">" else None,
            "max": num if op == "<" else None,
            "op": op,
            "label": label,
        }

    return None


def parse_reference(text: Optional[str]) -> Optional[ReferenceParsed]:
    """Parse reference range into structured data."""
    if not text:
        return None

    ref = text.strip()
    ref = re.sub(r"(?i)referencia:?", "", ref).strip()
    ref = ref.strip("()[]")
    ref = ref.replace("\u2013", "-").replace("\u2014", "-")
    if not ref:
        return None

    parts = [p.strip() for p in re.split(r"[;\n]+", ref) if p.strip()]
    if len(parts) > 1:
        bands = []
        for part in parts:
            band = _parse_band_line(part)
            if band:
                bands.append(band)
        if bands:
            return ReferenceParsed(type="bands", bands=bands)

    band = _parse_band_line(ref)
    if band:
        label = band.get("label")
        op = band.get("op")
        if label:
            return ReferenceParsed(type="bands", bands=[band])
        if op == "<":
            return ReferenceParsed(type="max_only", max=band.get("max"))
        if op == ">":
            return ReferenceParsed(type="min_only", min=band.get("min"))
        return ReferenceParsed(type="range", min=band.get("min"), max=band.get("max"))

    return None


def _split_reference(line: str) -> Tuple[str, Optional[str]]:
    ref_raw = None
    base = line
    m = re.search(r"\(([^)]*?)\)", line)
    if m:
        ref_raw = m.group(1).strip()
        base = (line[:m.start()] + " " + line[m.end():]).strip()

    if "REFERENCIA" in base.upper():
        parts = re.split(r"(?i)referencia:?", base, maxsplit=1)
        base = parts[0].strip()
        if len(parts) > 1:
            ref_raw = parts[1].strip()

    return base, ref_raw


def _is_section_header(line: str) -> bool:
    if not line:
        return False
    if any(ch.isdigit() for ch in line):
        return False
    text = line.strip()
    if len(text) < 4 or len(text) > 60:
        return False
    upper = _strip_diacritics(text).upper()
    if any(token in upper for token in _CATEGORICAL_VALUES):
        return False
    if "/" in text and re.search(r"[A-Za-z]", text):
        return False
    if ":" in text:
        return False
    upper_ratio = sum(1 for c in text if c.isupper()) / max(
        1, sum(1 for c in text if c.isalpha())
    )
    if upper_ratio < 0.6:
        return False
    header_keywords = {
        "RESULTADOS",
        "UNIDADES",
        "VALORES",
        "REFERENCIA",
        "NOTA",
        "METODO",
        "MUESTRA",
    }
    if any(k in upper for k in header_keywords):
        return False
    words = text.split()
    if any(hint in upper for hint in _SECTION_HINTS):
        return True
    if len(words) <= 4 and len(text) <= 35:
        return True
    return False


def _has_section_hint(line: str) -> bool:
    if not line:
        return False
    upper = _strip_diacritics(line).upper()
    return any(hint in upper for hint in _SECTION_HINTS)


def _detect_specimen(line: str) -> Optional[str]:
    normalized = _strip_diacritics(line).upper()
    if "MUESTRA ANALITICA" in normalized or "MUESTRA ANALITICA:" in normalized:
        for spec in _SPECIMEN_KEYWORDS:
            if spec in normalized:
                return spec
    for spec in _SPECIMEN_KEYWORDS:
        if re.search(rf"\b{re.escape(spec)}\b", normalized):
            return spec
    return None


def _detect_method(line: str) -> Optional[str]:
    normalized = _strip_diacritics(line).upper()
    if "METODO" in normalized:
        parts = re.split(r"(?i)metodo:?", line, maxsplit=1)
        if len(parts) > 1:
            method = parts[1].strip()
            return method or None
    return None


def _extract_value_and_unit(line: str) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[str], Optional[str]]:
    cleaned = line.strip()
    if not cleaned:
        return (None, None, None, None, None)

    upper = _strip_diacritics(cleaned).upper()
    cat_token = None
    for token in _CATEGORICAL_VALUES:
        if re.search(rf"\b{re.escape(token)}\b", upper):
            cat_token = token
            break

    num_match = re.search(r"([+-]?\d[\d.,]*)", cleaned)
    value_num = parse_number(num_match.group(1)) if num_match else None

    if value_num is None and not cat_token:
        return (None, None, None, None, None)

    value_type = "numeric" if value_num is not None else "categorical"
    value_cat = cat_token if value_num is None else None

    cut_idx = num_match.start() if num_match else upper.find(cat_token)
    name_part = cleaned[:cut_idx].strip(" :-") if cut_idx is not None else cleaned
    tail = cleaned[cut_idx + (len(num_match.group(1)) if num_match else len(cat_token)):]

    unit_raw = None
    if tail:
        unit_match = _UNIT_TOKEN_RE.search(tail)
        if unit_match:
            unit_raw = unit_match.group(0)

    return (value_type, value_num, value_cat, unit_raw, name_part)


def _looks_like_name_continuation(line: str) -> bool:
    if not line:
        return False
    if any(ch.isdigit() for ch in line):
        return False
    if len(line) > 80:
        return False
    return bool(re.search(r"[A-Za-z]", line))


def _is_band_only_line(line: str) -> bool:
    if not line:
        return False
    if re.search(r"[<>]\s*\d", line):
        return True
    if re.search(r"\d[\d.,]*\s*(?:a|to|\u2013|-|\u2014)\s*\d", line, re.IGNORECASE):
        return True
    return False


def parse_records_with_context(
    pages: Union[str, Sequence[str], Sequence[Dict[str, Union[int, str]]]],
) -> List[ParsedRecord]:
    """Parse text pages into structured records with context."""
    if isinstance(pages, str):
        pages_list = [{"page": 0, "text": pages}]
    else:
        pages_list = []
        for idx, page in enumerate(pages):
            if isinstance(page, str):
                pages_list.append({"page": idx, "text": page})
            else:
                pages_list.append({"page": int(page.get("page", idx)), "text": page.get("text", "")})

    records: List[ParsedRecord] = []
    current_section: List[str] = []
    current_specimen: Optional[str] = None
    current_method: Optional[str] = None
    pending_name_parts: List[str] = []
    pending_fragments: List[str] = []

    for page in pages_list:
        page_idx = int(page["page"])
        lines = normalize_text(str(page["text"]))
        for i, line in enumerate(lines):
            specimen = _detect_specimen(line)
            if specimen:
                current_specimen = specimen
                continue

            method = _detect_method(line)
            if method:
                current_method = method
                continue

            if _is_section_header(line):
                if not _has_section_hint(line) and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    base_next, _ = _split_reference(next_line)
                    value_type, _, _, _, _ = _extract_value_and_unit(base_next)
                    if value_type is not None:
                        pending_name_parts.append(line.strip(":"))
                        pending_fragments.append(line)
                        continue
                current_section = [line.strip()]
                pending_name_parts = []
                pending_fragments = []
                continue

            base, ref_raw = _split_reference(line)
            base = base.strip()

            if _is_band_only_line(base) and records:
                band = _parse_band_line(base)
                if band:
                    last = records[-1]
                    if last.ref_parsed and last.ref_parsed.type == "bands":
                        last.ref_parsed.bands = (last.ref_parsed.bands or []) + [band]
                    else:
                        last.ref_parsed = ReferenceParsed(type="bands", bands=[band])
                    last.ref_raw = (last.ref_raw or "") + ("; " if last.ref_raw else "") + base
                continue

            value_type, value_num, value_cat, unit_raw, name_part = _extract_value_and_unit(base)
            if value_type is None:
                if _looks_like_name_continuation(base):
                    pending_name_parts.append(base.strip(":"))
                    pending_fragments.append(line)
                else:
                    pending_name_parts = []
                    pending_fragments = []
                continue

            name_parts = pending_name_parts + [name_part] if name_part else pending_name_parts
            test_name_raw = " ".join(p for p in name_parts if p).strip()
            if not test_name_raw:
                continue

            raw_fragment = " ".join(pending_fragments + [line]).strip()
            pending_name_parts = []
            pending_fragments = []

            test_name_norm = normalize_analyte_name(test_name_raw)
            unit_norm = _normalize_unit(unit_raw)
            ref_parsed = parse_reference(ref_raw)

            section_path = current_section[:] if current_section else []
            series_key = "|".join(
                [
                    test_name_norm or "",
                    (current_specimen or ""),
                    (unit_norm or ""),
                    " / ".join(section_path),
                ]
            )

            records.append(
                ParsedRecord(
                    page=page_idx,
                    section_path=section_path,
                    specimen=current_specimen,
                    method=current_method,
                    test_name_raw=test_name_raw,
                    test_name_norm=test_name_norm,
                    value_type=value_type,
                    value_num=value_num,
                    value_cat=value_cat,
                    unit_raw=unit_raw,
                    unit_norm=unit_norm,
                    ref_raw=ref_raw,
                    ref_parsed=ref_parsed,
                    raw_fragment=raw_fragment,
                    series_key=series_key,
                )
            )

    return records

