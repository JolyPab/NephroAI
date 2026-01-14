"""Simple line-based lab parser for extracted PDF text."""

from dataclasses import dataclass
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

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
}

_SECTION_HINTS = {
    "PERFIL",
    "EXAMEN",
    "EVALUACION",
    "PANEL",
    "FUNCION",
    "LABORATORIO",
    "BIOQUIMICA",
    "HEMATOLOGIA",
    "MICROBIOLOGIA",
    "SEROLOGIA",
    "INMUNOLOGIA",
    "ORINA",
    "UROANALISIS",
}

_NOISE_PREFIXES = [
    "NUMERO DE SERVICIO",
    "PACIENTE",
    "GENERALES",
    "MEDICO",
    "FECHA",
    "IMP. DE RESULTADOS",
    "IMP DE RESULTADOS",
    "NUM. IMP",
    "NUM IMP",
    "PAG.",
    "PAG",
    "MUESTRA ANALITICA",
    "MUESTRA ANALITICA:",
    "METODO",
    "ANALITOS ACREDITADOS",
]

_TABLE_HEADERS = {
    "RESULTADOS",
    "UNIDADES",
    "VALORES DE",
    "REFERENCIA",
    "NOTA",
}


@dataclass
class ReferenceParsed:
    type: str
    min: Optional[float] = None
    max: Optional[float] = None
    bands: Optional[List[Dict[str, Optional[str]]]] = None


@dataclass
class Record:
    section_path: List[str]
    test_name_raw: str
    test_name_norm: str
    value_type: str
    value_num: Optional[float]
    value_cat: Optional[str]
    value_op: Optional[str]
    unit_raw: Optional[str]
    unit_norm: Optional[str]
    ref_raw: Optional[str]
    ref_parsed: Optional[ReferenceParsed]
    raw_fragment: str
    page: Optional[int] = None
    specimen: Optional[str] = None
    method: Optional[str] = None


def _strip_diacritics(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _compact(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", _strip_diacritics(text).upper())


def normalize_lines(text: str) -> List[str]:
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00d7", "x").replace("\u00b5", "u")
    lines = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line == ".":
            continue
        if re.fullmatch(r"[_\-\.\s]{3,}", line):
            continue
        line = re.sub(r"[_\-\.]{3,}", " ", line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line or line == ".":
            continue
        lines.append(line)
    return lines


def parse_number(value: str) -> Optional[float]:
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


def _is_noise_line(line: str) -> bool:
    compact = _compact(line)
    for prefix in _NOISE_PREFIXES:
        if compact.startswith(_compact(prefix)):
            return True
    if _compact(line) in {_compact(h) for h in _TABLE_HEADERS}:
        return True
    return False


def _looks_like_date_or_time(text: str) -> bool:
    if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", text):
        return True
    if re.search(r"\d{1,2}:\d{2}", text):
        return True
    upper = _strip_diacritics(text).upper()
    if "HRS" in upper or "HR" in upper:
        return True
    return False


def _is_section_header(line: str) -> bool:
    if _is_noise_line(line):
        return False
    if ":" in line:
        return False
    if any(ch.isdigit() for ch in line):
        return False
    words = line.split()
    if len(words) < 2 and len(line) < 15:
        return False
    if len(line) > 60:
        return False
    upper = _strip_diacritics(line).upper()
    if any(hint in upper for hint in _SECTION_HINTS):
        return True
    if len(line) >= 20 and len(words) >= 2:
        return True
    return False


def _looks_like_name(line: str) -> bool:
    if _is_noise_line(line):
        return False
    if _looks_like_date_or_time(line):
        return False
    if _is_section_header(line):
        return False
    return bool(re.search(r"[A-Za-z]", line))


def _looks_like_unit(line: str) -> bool:
    if _looks_like_date_or_time(line):
        return False
    if not re.search(r"[A-Za-z%]", line):
        return False
    if "/" in line or "%" in line or "^" in line:
        return True
    if re.search(r"x10", line, re.IGNORECASE):
        return True
    if re.search(r"\d", line):
        return True
    return False


def _normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    unit = unit.replace("\u00d7", "x").replace("\u00b5", "u")
    unit = re.sub(r"\s+", "", unit)
    return unit.upper() if unit else None


def _parse_reference_line(line: str) -> Optional[ReferenceParsed]:
    if not line:
        return None
    ref = line.strip()
    ref = re.sub(r"(?i)referencia:?", "", ref).strip()
    ref = ref.strip("()[]")
    ref = ref.replace("\u2013", "-").replace("\u2014", "-")
    if not ref:
        return None

    range_match = re.search(
        r"([+-]?\d[\d.,]*)\s*(?:a|to|\u2013|-|\u2014)\s*([+-]?\d[\d.,]*)",
        ref,
        flags=re.IGNORECASE,
    )
    if range_match:
        min_val = parse_number(range_match.group(1))
        max_val = parse_number(range_match.group(2))
        label = ref[range_match.end():].strip() or None
        if label:
            return ReferenceParsed(
                type="bands",
                bands=[{"min": min_val, "max": max_val, "op": None, "label": label}],
            )
        return ReferenceParsed(type="range", min=min_val, max=max_val)

    op_match = re.search(r"([<>]=?)\s*([+-]?\d[\d.,]*)", ref)
    if op_match:
        op = op_match.group(1)
        val = parse_number(op_match.group(2))
        label = ref[op_match.end():].strip() or None
        if label:
            return ReferenceParsed(
                type="bands",
                bands=[{"min": val if op.startswith(">") else None, "max": val if op.startswith("<") else None, "op": op, "label": label}],
            )
        if op.startswith(">"):
            return ReferenceParsed(type="min_only", min=val)
        return ReferenceParsed(type="max_only", max=val)

    return None


def _looks_like_reference(line: str) -> bool:
    return _parse_reference_line(line) is not None


def _parse_value_line(line: str) -> Optional[Tuple[str, Optional[float], Optional[str], Optional[str]]]:
    if _looks_like_reference(line):
        return None
    upper = _strip_diacritics(line).upper()
    if not re.search(r"\d", line):
        for token in _CATEGORICAL_VALUES:
            if upper == token:
                return ("categorical", None, token, None)
        return None

    m = re.fullmatch(r"\s*([<>]=?)?\s*([+-]?\d[\d.,]*)\s*", line)
    if not m:
        return None
    op = m.group(1)
    val = parse_number(m.group(2))
    if val is None:
        return None
    return ("numeric", val, None, op)


def _parse_inline_record(line: str, section_path: List[str]) -> Optional[Record]:
    if not re.search(r"[A-Za-z]", line) or not re.search(r"\d", line):
        upper = _strip_diacritics(line).upper()
        for token in _CATEGORICAL_VALUES:
            if token in upper:
                parts = re.split(rf"\\b{re.escape(token)}\\b", line, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) < 2:
                    return None
                name_part = parts[0].strip()
                tail = parts[1].strip()
                unit_raw = None
                if tail:
                    unit_match = re.search(r"[A-Za-z/%\^0-9\.\-]+", tail)
                    if unit_match:
                        unit_raw = unit_match.group(0)
                ref_parsed = _parse_reference_line(tail) if tail else None
                if not name_part:
                    return None
                return Record(
                    section_path=section_path[:],
                    test_name_raw=name_part,
                    test_name_norm=normalize_analyte_name(name_part),
                    value_type="categorical",
                    value_num=None,
                    value_cat=token,
                    value_op=None,
                    unit_raw=unit_raw,
                    unit_norm=_normalize_unit(unit_raw),
                    ref_raw=tail or None,
                    ref_parsed=ref_parsed,
                    raw_fragment=line,
                )
        return None

    m = re.search(r"([<>]=?)?\s*([+-]?\d[\d.,]*)", line)
    if not m:
        return None
    name_part = line[: m.start()].strip()
    tail = line[m.end() :].strip()
    if not name_part or not re.search(r"[A-Za-z]", name_part):
        return None

    op = m.group(1)
    val = parse_number(m.group(2))
    if val is None:
        return None

    unit_raw = None
    ref_raw = None
    if tail:
        unit_match = re.search(r"[A-Za-z/%\^0-9\.\-]+", tail)
        if unit_match:
            unit_raw = unit_match.group(0)
            ref_raw = tail[unit_match.end() :].strip() or None
        else:
            ref_raw = tail

    ref_parsed = _parse_reference_line(ref_raw) if ref_raw else None

    return Record(
        section_path=section_path[:],
        test_name_raw=name_part,
        test_name_norm=normalize_analyte_name(name_part),
        value_type="numeric",
        value_num=val,
        value_cat=None,
        value_op=op,
        unit_raw=unit_raw,
        unit_norm=_normalize_unit(unit_raw),
        ref_raw=ref_raw,
        ref_parsed=ref_parsed,
        raw_fragment=line,
    )


def parse(text: str) -> List[Record]:
    lines = normalize_lines(text)
    records: List[Record] = []
    pending_names: List[str] = []
    pending_fragments: List[str] = []
    inside_results = False
    section_path: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_noise_line(line):
            pending_names = []
            pending_fragments = []
            i += 1
            continue

        if _is_section_header(line):
            section_path = [line]
            pending_names = []
            pending_fragments = []
            i += 1
            continue

        inline = _parse_inline_record(line, section_path)
        if inline:
            if inline.unit_raw and _looks_like_date_or_time(inline.unit_raw):
                inline.unit_raw = None
                inline.unit_norm = None
            if inline.unit_norm or inline.ref_parsed or inside_results:
                records.append(inline)
                inside_results = True
            pending_names = []
            pending_fragments = []
            i += 1
            continue

        value_info = _parse_value_line(line)
        if value_info:
            if not pending_names:
                i += 1
                continue

            value_type, value_num, value_cat, value_op = value_info
            name_raw = " ".join(pending_names).strip()
            if not name_raw:
                pending_names = []
                pending_fragments = []
                i += 1
                continue

            raw_fragment = " ".join(pending_fragments + [line]).strip()
            pending_names = []
            pending_fragments = []

            unit_raw = None
            ref_raw = None
            j = i + 1

            if j < len(lines) and _looks_like_unit(lines[j]):
                if not _looks_like_date_or_time(lines[j]):
                    unit_raw = lines[j]
                    raw_fragment = f"{raw_fragment} {lines[j]}"
                j += 1

            if j < len(lines) and _looks_like_reference(lines[j]):
                ref_raw = lines[j]
                raw_fragment = f"{raw_fragment} {lines[j]}"
                j += 1
            elif not unit_raw and j < len(lines) and _looks_like_reference(lines[j]):
                ref_raw = lines[j]
                raw_fragment = f"{raw_fragment} {lines[j]}"
                j += 1

            unit_norm = _normalize_unit(unit_raw)
            if unit_raw and _looks_like_date_or_time(unit_raw):
                unit_raw = None
                unit_norm = None

            ref_parsed = _parse_reference_line(ref_raw) if ref_raw else None

            if unit_norm or ref_parsed or inside_results:
                records.append(
                    Record(
                        section_path=section_path[:],
                        test_name_raw=name_raw,
                        test_name_norm=normalize_analyte_name(name_raw),
                        value_type=value_type,
                        value_num=value_num,
                        value_cat=value_cat,
                        value_op=value_op,
                        unit_raw=unit_raw,
                        unit_norm=unit_norm,
                        ref_raw=ref_raw,
                        ref_parsed=ref_parsed,
                        raw_fragment=raw_fragment,
                    )
                )
                inside_results = True

            i = j
            continue

        if _looks_like_name(line):
            pending_names.append(line)
            pending_fragments.append(line)
        else:
            pending_names = []
            pending_fragments = []

        i += 1

    return records
