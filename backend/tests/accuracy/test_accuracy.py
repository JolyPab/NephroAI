"""
Accuracy tests for the V2 PDF extraction pipeline.

Usage:
    # Put PDF files in backend/tests/accuracy/fixtures/
    cd backend
    python -m pytest tests/accuracy/test_accuracy.py -v \\
        --html=tests/accuracy/report.html --self-contained-html

Requires OPENAI_API_KEY in environment.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from backend.v2.extractor import extract
from backend.tests.accuracy.judge import run_judge

FIXTURES_DIR = Path(__file__).parent / "fixtures"


_PDF_FIXTURES = sorted(FIXTURES_DIR.glob("*.pdf"))


@pytest.mark.parametrize("pdf_path", _PDF_FIXTURES, ids=[p.name for p in _PDF_FIXTURES])
def test_accuracy(pdf_path: Path, record_property):
    """For each PDF: extract, then judge. Fail on any critical issue."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    pdf_bytes = pdf_path.read_bytes()

    payload = asyncio.run(extract(pdf_bytes))
    extracted_json = payload.model_dump(mode="json")

    judge_result = run_judge(pdf_bytes, extracted_json)

    record_property("pdf_file", pdf_path.name)
    record_property("metrics_in_pdf", judge_result.total_metrics_in_pdf)
    record_property("metrics_extracted", judge_result.total_metrics_extracted)

    critical_issues = [i for i in judge_result.issues if i.severity == "critical"]
    warnings = [i for i in judge_result.issues if i.severity == "warning"]

    for idx, issue in enumerate(judge_result.issues):
        record_property(
            f"issue_{idx + 1}",
            f"[{issue.severity.upper()}] {issue.metric or '?'}.{issue.field or '?'}: "
            f"expected={issue.expected!r} got={issue.got!r} — {issue.description}",
        )

    if critical_issues:
        details = "\n".join(
            f"  - [{i.metric}] {i.field}: expected={i.expected!r} got={i.got!r} — {i.description}"
            for i in critical_issues
        )
        pytest.fail(
            f"{pdf_path.name}: {len(critical_issues)} critical issue(s):\n{details}\n"
            f"({len(warnings)} warning(s) — see HTML report)"
        )
