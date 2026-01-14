from backend.parsing.pipeline import parse_with_ocr_fallback


def test_ocr_fallback_triggered_records_zero():
    raw_text = "NUMERO DE SERVICIO: 123\nFECHA DE REGISTRO: 01/01/2025"

    def fake_select_pages(_pdf_bytes):
        return [0]

    def fake_ocr(_pdf_bytes, _pages):
        return [
            {
                "page": 0,
                "text": "ANTIGENO PROSTATICO ESPECIFICO 0.65 ng/mL 0.0 a 2.5",
            }
        ]

    result = parse_with_ocr_fallback(
        b"%PDF-1.4",
        raw_text,
        select_pages_func=fake_select_pages,
        ocr_func=fake_ocr,
    )

    assert result["triggered_by"] == "records_zero"
    assert result["metrics"]["records_count"] >= 1
