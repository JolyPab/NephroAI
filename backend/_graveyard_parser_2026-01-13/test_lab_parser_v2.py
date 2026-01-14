from pathlib import Path

from lab_parser_v2 import parse


def _load_records():
    text_path = Path(__file__).with_name("extracted_text.txt")
    text = text_path.read_text(encoding="utf-8", errors="replace")
    return parse(text)


def _find_record(records, name, predicate):
    for rec in records:
        if rec.test_name_norm == name and predicate(rec):
            return rec
    return None


def test_creatinina_numeric_range():
    records = _load_records()
    rec = _find_record(
        records,
        "CREATININA",
        lambda r: r.value_num is not None and abs(r.value_num - 2.46) < 0.01,
    )
    assert rec is not None
    assert rec.unit_norm == "MG/DL"
    assert rec.ref_parsed and rec.ref_parsed.min == 0.7 and rec.ref_parsed.max == 1.3


def test_inmunoglobulina_g_thousands():
    records = _load_records()
    rec = _find_record(
        records,
        "INMUNOGLOBULINA G",
        lambda r: r.value_num is not None and abs(r.value_num - 1313.0) < 0.01,
    )
    assert rec is not None
    assert rec.unit_norm == "MG/DL"
    assert rec.ref_parsed and rec.ref_parsed.max == 1310


def test_albumina_operator():
    records = _load_records()
    rec = _find_record(
        records,
        "ALBUMINA",
        lambda r: r.value_num is not None and abs(r.value_num - 150) < 0.01,
    )
    assert rec is not None
    assert rec.value_op == ">"
    assert rec.unit_norm == "MG/L"
    assert rec.ref_parsed and rec.ref_parsed.max == 23.8


def test_glucosa_categorical():
    records = _load_records()
    rec = _find_record(
        records,
        "GLUCOSA",
        lambda r: r.value_cat == "NEGATIVO",
    )
    assert rec is not None
    assert rec.value_type == "categorical"
    assert rec.unit_norm == "MG/DL"


def test_no_header_records():
    records = _load_records()
    forbidden = {"NUMERO DE SERVICIO", "FECHA DE REGISTRO", "GENERALES"}
    for rec in records:
        for key in forbidden:
            assert key not in rec.test_name_norm
