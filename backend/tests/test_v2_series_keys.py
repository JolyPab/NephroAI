from backend.v2.extractor import _assign_series_keys
from backend.v2.schemas import Context, ImportV2, MetricV2, ReferenceType, ReferenceV2, Specimen


def _make_metric(raw_name: str, specimen: Specimen, value_numeric, value_text):
    return MetricV2(
        raw_name=raw_name,
        analyte_key="PLACEHOLDER",
        specimen=specimen,
        context=Context.unknown,
        value_numeric=value_numeric,
        value_text=value_text,
        unit="mg/dL",
        reference=ReferenceV2(
            type=ReferenceType.none,
            min=None,
            max=None,
            threshold=None,
            categories=None,
            stages=None,
            ref_text_raw=None,
        ),
        evidence="x",
        page=1,
    )


def test_assign_series_keys_splits_by_specimen_and_value_kind():
    payload = ImportV2(
        analysis_date=None,
        report_date=None,
        patient_age=None,
        patient_sex=None,
        metrics=[
            _make_metric("GLUCOSA", Specimen.serum, 91.8, None),
            _make_metric("GLUCOSA", Specimen.urine, None, "NEGATIVO"),
        ],
    )

    out = _assign_series_keys(payload)
    keys = [m.analyte_key for m in out.metrics]
    assert keys[0] == "GLUCOSA__SERUM__NUM"
    assert keys[1] == "GLUCOSA__URINE__TEXT"

