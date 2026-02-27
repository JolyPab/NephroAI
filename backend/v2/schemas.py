from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class Specimen(str, Enum):
    blood = "blood"
    serum = "serum"
    plasma = "plasma"
    urine = "urine"
    stool = "stool"
    saliva = "saliva"
    csf = "csf"
    unknown = "unknown"


class Context(str, Enum):
    fasting = "fasting"
    postprandial = "postprandial"
    random = "random"
    baseline = "baseline"
    unknown = "unknown"


class ReferenceType(str, Enum):
    range = "range"
    max = "max"
    min = "min"
    categorical = "categorical"
    staged = "staged"
    none = "none"


class ReferenceCategory(BaseModel):
    label: str
    min: float | None
    max: float | None


class ReferenceStage(BaseModel):
    label: str
    min: float | None
    max: float | None


class ReferenceV2(BaseModel):
    type: ReferenceType
    min: float | None
    max: float | None
    threshold: float | None
    categories: list[ReferenceCategory] | None
    stages: list[ReferenceStage] | None
    ref_text_raw: str | None

    @model_validator(mode="after")
    def _validate_reference_consistency(self) -> "ReferenceV2":
        ref_type = self.type
        min_val = self.min
        max_val = self.max
        threshold = self.threshold
        categories = self.categories
        stages = self.stages

        if ref_type == ReferenceType.range:
            if min_val is None or max_val is None:
                raise ValueError("ReferenceV2.type=range requires both min and max.")
            if threshold is not None or categories is not None or stages is not None:
                raise ValueError("ReferenceV2.type=range forbids threshold/categories/stages.")
        elif ref_type in {ReferenceType.max, ReferenceType.min}:
            if threshold is None:
                raise ValueError("ReferenceV2.type=max|min requires threshold.")
            if min_val is not None or max_val is not None or categories is not None or stages is not None:
                raise ValueError("ReferenceV2.type=max|min forbids min/max/categories/stages.")
        elif ref_type == ReferenceType.categorical:
            if not categories:
                raise ValueError("ReferenceV2.type=categorical requires categories.")
            if min_val is not None or max_val is not None or threshold is not None or stages is not None:
                raise ValueError("ReferenceV2.type=categorical forbids min/max/threshold/stages.")
        elif ref_type == ReferenceType.staged:
            if not stages:
                raise ValueError("ReferenceV2.type=staged requires stages.")
            if min_val is not None or max_val is not None or threshold is not None or categories is not None:
                raise ValueError("ReferenceV2.type=staged forbids min/max/threshold/categories.")
        elif ref_type == ReferenceType.none:
            if (
                min_val is not None
                or max_val is not None
                or threshold is not None
                or categories is not None
                or stages is not None
            ):
                raise ValueError("ReferenceV2.type=none forbids min/max/threshold/categories/stages.")

        return self


class MetricV2(BaseModel):
    raw_name: str
    analyte_key: str
    specimen: Specimen
    context: Context
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    reference: ReferenceV2
    evidence: str
    page: int | None

    @model_validator(mode="after")
    def _validate_value_choice(self) -> "MetricV2":
        has_num = self.value_numeric is not None
        has_text = self.value_text is not None and str(self.value_text).strip() != ""
        if has_num and has_text:
            raise ValueError("MetricV2 requires exactly one of value_numeric or value_text.")
        if not has_num and not has_text:
            if self.reference.type == ReferenceType.none:
                return self
            raise ValueError("MetricV2 requires at least one of value_numeric or value_text.")
        return self


class ImportV2(BaseModel):
    # analysis_date is used for charting.
    # If multiple dates exist, LLM should pick the analysis date (fecha de ingreso / collection date),
    # not the print date. If unsure, choose the earliest date and add warning "DATE_AMBIGUOUS".
    analysis_date: datetime | None
    report_date: datetime | None
    patient_age: int | None
    patient_sex: str | None
    metrics: list[MetricV2]
    warnings: list[str] = Field(default_factory=list)


class V2CreateDocumentResponse(BaseModel):
    document_id: str
    analysis_date: str | None
    num_metrics: int


class V2CreateDocumentDuplicateResponse(BaseModel):
    status: Literal["duplicate"]
    document_id: str
    analysis_date: str | None
    num_metrics: int


class V2AnalyteItemResponse(BaseModel):
    analyte_key: str
    raw_name: str | None = None
    last_value_numeric: float | None
    last_value_text: str | None
    last_date: str | None
    unit: str | None


class V2SeriesPointResponse(BaseModel):
    t: str | None
    y: float | None
    text: str | None
    page: int | None
    evidence: str | None


class V2SeriesResponse(BaseModel):
    analyte_key: str
    raw_name: str | None = None
    series_type: Literal["numeric", "text", "binary", "ordinal"]
    unit: str | None
    reference: dict[str, Any] | None
    points: list[V2SeriesPointResponse]


class V2DocumentInfoResponse(BaseModel):
    id: str
    user_id: int
    document_hash: str
    source_filename: str | None
    analysis_date: str | None
    report_date: str | None
    created_at: str | None


class V2DocumentMetricResponse(BaseModel):
    id: str
    document_id: str
    analyte_key: str
    raw_name: str
    specimen: str
    context: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    reference_json: dict[str, Any] | None
    page: int | None
    evidence: str | None


class V2DocumentDetailResponse(BaseModel):
    document: V2DocumentInfoResponse
    metrics: list[V2DocumentMetricResponse]


class V2DocumentListItemResponse(BaseModel):
    id: str
    source_filename: str | None
    analysis_date: str | None
    report_date: str | None
    created_at: str | None
    num_metrics: int


class V2DeleteDocumentResponse(BaseModel):
    status: Literal["deleted"]
    document_id: str
    num_metrics_deleted: int


class V2DoctorPatientResponse(BaseModel):
    patient_id: int
    display_name: str | None
    email: str | None
    granted_at: str | None
    latest_analysis_date: str | None


class V2DoctorNoteResponse(BaseModel):
    id: str
    analyte_key: str
    t: str
    note: str
    doctor_id: int
    doctor_name: str | None
    updated_at: str


class V2UpsertDoctorNoteRequest(BaseModel):
    analyte_key: str
    t: datetime
    note: str


"""
Example JSON (from sample-style PDF: GLUCOSA, CREATININA, eGFR staged)
{
  "analysis_date": "2023-07-01T00:00:00",
  "report_date": "2023-07-01T00:00:00",
  "patient_age": 52,
  "patient_sex": "M",
  "metrics": [
    {
      "raw_name": "GLUCOSA",
      "analyte_key": "GLUCOSA",
      "specimen": "serum",
      "context": "fasting",
      "value_numeric": 94.2,
      "value_text": null,
      "unit": "mg/dL",
      "reference": {
        "type": "range",
        "min": 70.0,
        "max": 100.0,
        "threshold": null,
        "categories": null,
        "stages": null,
        "ref_text_raw": "70 a 100"
      },
      "evidence": "GLUCOSA 94.2 mg/dL 70 a 100",
      "page": 1
    },
    {
      "raw_name": "CREATININA",
      "analyte_key": "CREATININA",
      "specimen": "serum",
      "context": "random",
      "value_numeric": 1.12,
      "value_text": null,
      "unit": "mg/dL",
      "reference": {
        "type": "range",
        "min": 0.7,
        "max": 1.3,
        "threshold": null,
        "categories": null,
        "stages": null,
        "ref_text_raw": "0.7 a 1.3"
      },
      "evidence": "CREATININA 1.12 mg/dL 0.7 a 1.3",
      "page": 1
    },
    {
      "raw_name": "TFG (eGFR)",
      "analyte_key": "EGFR",
      "specimen": "serum",
      "context": "baseline",
      "value_numeric": 58.0,
      "value_text": null,
      "unit": "mL/min/1.73m2",
      "reference": {
        "type": "staged",
        "min": null,
        "max": null,
        "threshold": null,
        "categories": null,
        "stages": [
          { "label": "G1", "min": 90.0, "max": null },
          { "label": "G2", "min": 60.0, "max": 89.9 },
          { "label": "G3A", "min": 45.0, "max": 59.9 },
          { "label": "G3B", "min": 30.0, "max": 44.9 },
          { "label": "G4", "min": 15.0, "max": 29.9 },
          { "label": "G5", "min": null, "max": 14.9 }
        ],
        "ref_text_raw": "G1>=90; G2 60-89; G3A 45-59; G3B 30-44; G4 15-29; G5<15"
      },
      "evidence": "TFG 58 mL/min/1.73m2",
      "page": 1
    }
  ],
  "warnings": []
}
"""
