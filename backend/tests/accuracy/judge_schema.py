# backend/tests/accuracy/judge_schema.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class JudgeIssue(BaseModel):
    severity: Literal["critical", "warning"]
    metric: str | None  # raw_name or analyte_key from PDF
    field: str | None   # which field is wrong (value_numeric, unit, etc.)
    expected: str | None
    got: str | None
    description: str


class JudgeResult(BaseModel):
    issues: list[JudgeIssue]
    total_metrics_in_pdf: int
    total_metrics_extracted: int
