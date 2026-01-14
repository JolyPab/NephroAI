from pdf_context_parser import (
    normalize_text,
    parse_number,
    parse_reference,
    parse_records_with_context,
)


def test_parse_number():
    assert parse_number("1,000") == 1000
    assert parse_number("1,304.00") == 1304.00
    assert parse_number("9.14") == 9.14
    assert parse_number("9,14") == 9.14


def test_reference_range():
    ref = parse_reference("70 \u2013 100")
    assert ref and ref.type == "range"
    assert ref.min == 70
    assert ref.max == 100


def test_reference_min_max_only():
    ref_min = parse_reference("> 160 Alto")
    assert ref_min and ref_min.type == "bands"
    assert ref_min.bands[0]["min"] == 160

    ref_max = parse_reference("< 130 Optimo")
    assert ref_max and ref_max.type == "bands"
    assert ref_max.bands[0]["max"] == 130


def test_numeric_and_categorical_records():
    text = "GLUCOSA 94.20 mg/dL (Referencia: 70 \u2013 100)"
    records = parse_records_with_context(text)
    assert len(records) == 1
    rec = records[0]
    assert rec.test_name_norm == "GLUCOSA"
    assert rec.value_type == "numeric"
    assert rec.value_num == 94.2
    assert rec.unit_norm == "MG/DL"
    assert rec.ref_parsed and rec.ref_parsed.type == "range"

    text = "GLUCOSA NEGATIVO mg/dL (Referencia: 2 \u2013 20)"
    records = parse_records_with_context(text)
    assert len(records) == 1
    rec = records[0]
    assert rec.value_type == "categorical"
    assert rec.value_cat == "NEGATIVO"
    assert rec.value_num is None


def test_thousand_separator_reference():
    text = "LIPIDOS TOTALES 800 mg/dL (Referencia: 400 a 1,000)"
    records = parse_records_with_context(text)
    assert len(records) == 1
    rec = records[0]
    assert rec.value_num == 800
    assert rec.ref_parsed and rec.ref_parsed.max == 1000


def test_bands_reference_lines():
    text = "\n".join(
        [
            "COLESTEROL TOTAL 220 mg/dL",
            "100 a 200 Bajo Riesgo",
            "201 a 239 Riesgo Moderado",
            "240 a 500 Alto Riesgo",
        ]
    )
    records = parse_records_with_context(text)
    assert len(records) == 1
    rec = records[0]
    assert rec.ref_parsed and rec.ref_parsed.type == "bands"
    assert len(rec.ref_parsed.bands) == 3


def test_multiline_name():
    text = "\n".join(
        [
            "CONCENTRACION MEDIA DE HEMOGLOBINA",
            "CORPUSCULAR: 33.3 gr/dL (Referencia: 32 \u2013 34.5)",
        ]
    )
    records = parse_records_with_context(text)
    assert len(records) == 1
    rec = records[0]
    assert "CONCENTRACION MEDIA DE HEMOGLOBINA CORPUSCULAR" in rec.test_name_norm


def test_series_key_collision_by_specimen():
    text = "\n".join(
        [
            "Muestra Analitica: SUERO",
            "GLUCOSA 94.2 mg/dL",
            "Muestra Analitica: ORINA",
            "GLUCOSA NEGATIVO mg/dL",
        ]
    )
    records = parse_records_with_context(text)
    assert len(records) == 2
    assert records[0].series_key != records[1].series_key
