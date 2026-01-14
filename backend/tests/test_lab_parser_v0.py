from datetime import date
from pathlib import Path
import re
import unicodedata

import pytest

from backend.parsing.lab_parser_v0 import parse_raw_text
from backend.parsing.pipeline import extract_report_date

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "extracted_text.txt"
PDF_B_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "raw_text_013231840002.txt"

SAMPLE_LINES = [
    "CREATININA 2.46 mg/dL 0.7 a 1.3",
    "INMUNOGLOBULINA G 1,313.00 mg/dL 595 a 1310",
    "ALBUMINA >150 mg/L 0 a 23.8",
    "GLUCOSA NEGATIVO mg/dL 2 a 20",
]


def _load_fixture_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8", errors="ignore")


def _load_sample_text() -> str:
    return "\n".join(SAMPLE_LINES)


def _find_record(records, name, value_num=None, value_cat=None):
    name = name.upper().strip()
    for record in records:
        if record["test_name_raw"].strip().upper() != name:
            continue
        if value_num is not None and record["value_num"] != value_num:
            continue
        if value_cat is not None and record["value_cat"] != value_cat:
            continue
        return record
    return None


def _normalize_name(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = " ".join(normalized.split()).upper()
    return normalized


def test_parse_numeric():
    records = parse_raw_text(_load_sample_text())
    record = _find_record(records, "CREATININA")
    assert record is not None
    assert record["value_type"] == "numeric"
    assert record["value_num"] == pytest.approx(2.46)
    assert record["unit_raw"] == "mg/dL"
    assert record["ref_min"] == pytest.approx(0.7)
    assert record["ref_max"] == pytest.approx(1.3)


def test_parse_thousand():
    records = parse_raw_text(_load_sample_text())
    record = _find_record(records, "INMUNOGLOBULINA G")
    assert record is not None
    assert record["value_num"] == pytest.approx(1313.0)
    assert record["unit_raw"] == "mg/dL"
    assert record["ref_min"] == pytest.approx(595.0)
    assert record["ref_max"] == pytest.approx(1310.0)


def test_parse_operator():
    records = parse_raw_text(_load_sample_text())
    record = _find_record(records, "ALBUMINA")
    assert record is not None
    assert record["value_operator"] == ">"
    assert record["value_num"] == pytest.approx(150.0)
    assert record["unit_raw"] == "mg/L"


def test_parse_categorical():
    records = parse_raw_text(_load_sample_text())
    record = _find_record(records, "GLUCOSA", value_cat="NEGATIVO")
    assert record is not None
    assert record["value_type"] == "categorical"
    assert record["value_num"] is None
    assert record["unit_raw"] == "mg/dL"


def test_headers_not_parsed():
    records = parse_raw_text(_load_fixture_text())
    bad_prefixes = ("NUMERO DE SERVICIO", "PACIENTE", "FECHA", "PAG.")
    for record in records:
        name = _normalize_name(record["test_name_raw"])
        assert not name.startswith(bad_prefixes)


def test_fixture_parsing_basics():
    fixture_text = _load_fixture_text()
    header_match = re.search(
        r"FECHA\s+DE\s+REGISTRO\s*:?\s*([0-3]?\d/[0-1]?\d/\d{4})",
        fixture_text,
        flags=re.IGNORECASE,
    )
    assert header_match is not None
    date_str = header_match.group(1)
    assert re.fullmatch(r"[0-3]?\d/[0-1]?\d/\d{4}", date_str)
    day, month, year = [int(part) for part in date_str.split("/")]
    expected_date = date(year, month, day)

    report_date, report_source = extract_report_date(fixture_text)
    assert report_date == expected_date
    assert report_source == "registro"
    records = parse_raw_text(
        fixture_text,
        default_date=report_date,
        taken_at_source=report_source,
    )
    assert len(records) >= 30
    assert any("CREATININA" in _normalize_name(r["test_name_raw"]) for r in records)
    assert all(_normalize_name(r["test_name_raw"]) != "X" for r in records)

    def _series_key(record) -> str:
        name = _normalize_name(record.get("test_name_raw") or "")
        specimen = _normalize_name(record.get("specimen") or "")
        section = _normalize_name(record.get("section") or "")
        unit = record.get("unit_norm") or record.get("unit_raw") or ""
        unit = " ".join(unit.split()).upper()
        return "|".join([name, specimen, unit, section])

    series_keys = [_series_key(r) for r in records if (r.get("test_name_raw") or "").strip()]
    assert len(series_keys) == len(set(series_keys))

    sections = {_normalize_name(r["section"] or "") for r in records}
    assert "EVALUACION RENAL" in sections
    assert any("PERFIL LIPIDOS" in section for section in sections)
    assert "LIMITE ALTO" not in sections

    taken_at_values = {r.get("taken_at") for r in records}
    taken_at_sources = {r.get("taken_at_source") for r in records}
    assert taken_at_values == {report_date}
    assert taken_at_sources == {report_source}
    assert report_date != date.today()


def test_pdf_b_fixture_psa_present():
    text = PDF_B_FIXTURE_PATH.read_text(encoding="utf-8", errors="ignore")
    records = parse_raw_text(text)
    assert len(records) >= 1
    parsed_names = [_normalize_name(r["test_name_raw"]) for r in records]
    assert any("ANTIGENO PROSTATICO ESPECIFICO" in name for name in parsed_names)


def test_extract_report_date_priority():
    sample = (
        "FECHA DE LIBERACION: 06/07/2023\n"
        "FECHA DE REGISTRO: 03/07/2023\n"
        "FECHA DE TOMA: 01/07/2023\n"
    )
    report_date, report_source = extract_report_date(sample)
    assert report_date == date(2023, 7, 1)
    assert report_source == "toma"

    fallback = "FECHA DE LIBERACION: 06/07/2023"
    report_date, report_source = extract_report_date(fallback)
    assert report_date == date(2023, 7, 6)
    assert report_source == "liberacion"

    missing = "SIN FECHA EN ESTE TEXTO"
    report_date, report_source = extract_report_date(missing)
    assert report_date is None
    assert report_source == "missing"
