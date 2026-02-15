import pytest

from backend.v2.extractor import _normalize_scientific_units
from backend.v2.schemas import (
    Context,
    ImportV2,
    MetricV2,
    ReferenceType,
    ReferenceV2,
    Specimen,
)


def _make_payload(unit: str, value: float, ref_max: float) -> ImportV2:
    metric = MetricV2(
        raw_name="TEST",
        analyte_key="TEST_SERUM",
        specimen=Specimen.serum,
        context=Context.random,
        value_numeric=value,
        value_text=None,
        unit=unit,
        reference=ReferenceV2(
            type=ReferenceType.range,
            min=0.0,
            max=ref_max,
            threshold=None,
            categories=None,
            stages=None,
            ref_text_raw="0 - 1",
        ),
        evidence="TEST 1",
        page=1,
    )
    return ImportV2(
        analysis_date=None,
        report_date=None,
        patient_age=None,
        patient_sex=None,
        metrics=[metric],
        warnings=[],
    )


def test_normalize_scientific_units_divide_x10_6():
    payload = _make_payload("x10^6/mm3", 5_800_000, 6.3)
    out = _normalize_scientific_units(payload)
    assert out.metrics[0].value_numeric == pytest.approx(5.8)


def test_normalize_scientific_units_divide_x10_3():
    payload = _make_payload("x10^3/mm3", 7600, 10.0)
    out = _normalize_scientific_units(payload)
    assert out.metrics[0].value_numeric == pytest.approx(7.6)


def test_normalize_scientific_units_skip_small_value():
    payload = _make_payload("x10^6/mm3", 5.8, 6.3)
    out = _normalize_scientific_units(payload)
    assert out.metrics[0].value_numeric == pytest.approx(5.8)
