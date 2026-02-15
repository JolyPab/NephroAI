from types import SimpleNamespace

from backend.main import _classify_v2_series_type


def _row(value_numeric, value_text):
    metric = SimpleNamespace(value_numeric=value_numeric, value_text=value_text)
    return (metric, None, None)


def test_v2_series_type_numeric():
    rows = [
        _row(1.2, None),
        _row(1.4, ""),
        _row(0.9, None),
    ]
    assert _classify_v2_series_type(rows) == "numeric"


def test_v2_series_type_binary():
    rows = [
        _row(None, "NEGATIVO"),
        _row(None, "Positivo"),
        _row(None, "No reactivo"),
    ]
    assert _classify_v2_series_type(rows) == "binary"


def test_v2_series_type_ordinal():
    rows = [
        _row(None, "+"),
        _row(None, "++"),
        _row(None, "++++"),
        _row(None, "-"),  # ignored as missing-like
    ]
    assert _classify_v2_series_type(rows) == "ordinal"


def test_v2_series_type_text_fallback():
    rows = [
        _row(None, "few"),
        _row(None, "1-2"),
        _row(None, "cloudy"),
    ]
    assert _classify_v2_series_type(rows) == "text"
