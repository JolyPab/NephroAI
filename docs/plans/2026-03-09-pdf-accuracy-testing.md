# PDF Accuracy Testing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an LLM-as-judge accuracy test suite that verifies the V2 PDF extraction pipeline parses medical lab reports correctly, with pytest pass/fail output and an HTML report.

**Architecture:** For each PDF fixture, run `extract()` to get `ImportV2`, then call a second GPT instance ("judge") that receives both the original PDF and the extracted JSON and audits completeness/correctness. pytest fails on any critical issue; `pytest-html` generates a browsable report.

**Tech Stack:** Python, pytest, pytest-html, OpenAI File API (`client.responses.parse`), Pydantic v2

---

### Task 1: Install pytest-html and create directory structure

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/accuracy/__init__.py`
- Create: `backend/tests/accuracy/fixtures/.gitkeep`

**Step 1: Add pytest-html to requirements**

Open `backend/requirements.txt` and append:
```
pytest-html
```

**Step 2: Install it**

```bash
cd backend && pip install pytest-html
```
Expected: `Successfully installed pytest-html-X.X.X`

**Step 3: Create the accuracy test package**

```bash
mkdir -p backend/tests/accuracy/fixtures
touch backend/tests/accuracy/__init__.py
touch backend/tests/accuracy/fixtures/.gitkeep
```

**Step 4: Commit**

```bash
git add backend/requirements.txt backend/tests/accuracy/
git commit -m "chore: add pytest-html, create accuracy test scaffold"
```

---

### Task 2: Write JudgeResult schema

**Files:**
- Create: `backend/tests/accuracy/judge_schema.py`

**Step 1: Write the file**

```python
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
```

**Step 2: Write a quick smoke test**

```python
# backend/tests/accuracy/test_judge_schema.py
from backend.tests.accuracy.judge_schema import JudgeResult, JudgeIssue


def test_judge_result_parses():
    r = JudgeResult(
        issues=[
            JudgeIssue(
                severity="critical",
                metric="GLUCOSA",
                field="value_numeric",
                expected="94.5",
                got="94.2",
                description="Value differs",
            )
        ],
        total_metrics_in_pdf=10,
        total_metrics_extracted=9,
    )
    assert len(r.issues) == 1
    assert r.issues[0].severity == "critical"
```

**Step 3: Run to verify it passes**

```bash
cd backend && python -m pytest tests/accuracy/test_judge_schema.py -v
```
Expected: `PASSED`

**Step 4: Commit**

```bash
git add backend/tests/accuracy/judge_schema.py backend/tests/accuracy/test_judge_schema.py
git commit -m "feat: add JudgeResult pydantic schema for accuracy audit"
```

---

### Task 3: Write judge prompt

**Files:**
- Create: `backend/tests/accuracy/judge_prompt.py`

**Step 1: Write the file**

```python
# backend/tests/accuracy/judge_prompt.py

JUDGE_SYSTEM_PROMPT = """
You are a clinical laboratory data extraction auditor.

You will receive:
1. A PDF of a medical laboratory report.
2. A JSON object representing what an automated system extracted from that PDF.

Your task: audit the extraction for completeness and correctness.

Return ONLY valid JSON matching the JudgeResult schema. No markdown. No explanations.

JudgeResult schema:
{
  "issues": [
    {
      "severity": "critical" | "warning",
      "metric": "<raw name from PDF or null>",
      "field": "<which field: value_numeric | unit | reference | raw_name | specimen | analysis_date | missing_metric | null>",
      "expected": "<what the PDF says, or null>",
      "got": "<what the extraction says, or null>",
      "description": "<brief explanation>"
    }
  ],
  "total_metrics_in_pdf": <int, count of distinct test rows in the PDF>,
  "total_metrics_extracted": <int, count of metrics in the provided JSON>
}

Severity rules:
- CRITICAL: missing metric (row in PDF but not in JSON), wrong numeric value (>1% deviation),
  wrong unit of measurement, wrong reference range boundaries.
- WARNING: inaccurate raw_name (minor spelling), wrong specimen classification,
  missing or wrong analysis_date, minor reference range wording differences.

Instructions:
- Count every distinct test row in the PDF as a metric (including qualitative/text results).
- Compare each extracted metric value against the PDF source.
- If a numeric value differs by more than 1%, flag as critical with expected/got.
- If the unit is different (e.g. mg/dL vs mmol/L), flag as critical.
- If a metric present in the PDF is completely absent from the JSON, flag as critical with field="missing_metric".
- If reference range min/max differ from the PDF, flag as critical.
- Do NOT flag issues that are not real discrepancies.
- Return an empty issues list if extraction is perfect.

Return ONLY JSON.
"""
```

**Step 2: No test needed** — this is a string constant, verified by the integration test in Task 4.

**Step 3: Commit**

```bash
git add backend/tests/accuracy/judge_prompt.py
git commit -m "feat: add LLM judge system prompt for PDF accuracy audit"
```

---

### Task 4: Write judge.py

**Files:**
- Create: `backend/tests/accuracy/judge.py`

**Step 1: Write the file**

```python
# backend/tests/accuracy/judge.py
from __future__ import annotations

import asyncio
import json
import os

from openai import AsyncOpenAI

from backend.tests.accuracy.judge_prompt import JUDGE_SYSTEM_PROMPT
from backend.tests.accuracy.judge_schema import JudgeResult

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


async def judge_extraction(pdf_bytes: bytes, extracted_json: dict) -> JudgeResult:
    """
    Upload the PDF and extracted JSON to GPT and ask it to audit the extraction.
    Returns a JudgeResult with any issues found.
    """
    client = _get_client()
    uploaded_file = None
    try:
        uploaded_file = await client.files.create(
            file=("report.pdf", pdf_bytes, "application/pdf"),
            purpose="assistants",
        )
        response = await client.responses.parse(
            model="gpt-4o",
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": JUDGE_SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Extracted JSON:\n{json.dumps(extracted_json, indent=2, ensure_ascii=False)}",
                        },
                        {"type": "input_file", "file_id": uploaded_file.id},
                    ],
                },
            ],
            text_format=JudgeResult,
        )
        parsed = response.output_parsed
        if isinstance(parsed, JudgeResult):
            return parsed
        return JudgeResult.model_validate(parsed)
    finally:
        if uploaded_file is not None:
            try:
                await client.files.delete(uploaded_file.id)
            except Exception:
                pass


def run_judge(pdf_bytes: bytes, extracted_json: dict) -> JudgeResult:
    """Sync wrapper for use in pytest."""
    return asyncio.run(judge_extraction(pdf_bytes, extracted_json))
```

**Step 2: No unit test for judge.py** — it makes real API calls; it will be exercised end-to-end in Task 5. Instead write a mock test to verify it handles the response correctly:

```python
# backend/tests/accuracy/test_judge.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.tests.accuracy.judge import judge_extraction
from backend.tests.accuracy.judge_schema import JudgeResult


@pytest.mark.asyncio
async def test_judge_returns_judge_result():
    fake_result = JudgeResult(
        issues=[],
        total_metrics_in_pdf=5,
        total_metrics_extracted=5,
    )

    mock_response = MagicMock()
    mock_response.output_parsed = fake_result

    mock_client = MagicMock()
    mock_client.files.create = AsyncMock(return_value=MagicMock(id="file-123"))
    mock_client.files.delete = AsyncMock()
    mock_client.responses.parse = AsyncMock(return_value=mock_response)

    with patch("backend.tests.accuracy.judge._get_client", return_value=mock_client):
        result = await judge_extraction(b"fake-pdf", {"metrics": []})

    assert isinstance(result, JudgeResult)
    assert result.total_metrics_in_pdf == 5
```

**Step 3: Install pytest-asyncio if needed**

```bash
pip install pytest-asyncio
```

Add to `backend/requirements.txt`:
```
pytest-asyncio
```

**Step 4: Run mock test**

```bash
cd backend && python -m pytest tests/accuracy/test_judge.py -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add backend/tests/accuracy/judge.py backend/tests/accuracy/test_judge.py backend/requirements.txt
git commit -m "feat: add judge.py — LLM auditor for PDF extraction accuracy"
```

---

### Task 5: Write the main accuracy test

**Files:**
- Create: `backend/tests/accuracy/test_accuracy.py`

**Step 1: Write the test**

```python
# backend/tests/accuracy/test_accuracy.py
"""
Accuracy tests for the V2 PDF extraction pipeline.

Usage:
    # Put PDF files in backend/tests/accuracy/fixtures/
    cd backend
    python -m pytest tests/accuracy/test_accuracy.py -v \
        --html=tests/accuracy/report.html --self-contained-html

Requires OPENAI_API_KEY in environment.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.v2.extractor import extract
from backend.tests.accuracy.judge import run_judge

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _get_pdf_fixtures() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.pdf"))


def pytest_configure(config):
    """Skip all accuracy tests if no PDFs found."""
    pass


# Parametrize over every PDF in fixtures/
@pytest.mark.parametrize(
    "pdf_path",
    _get_pdf_fixtures(),
    ids=[p.name for p in _get_pdf_fixtures()],
)
def test_accuracy(pdf_path: Path, record_property):
    """
    For each PDF: extract, then judge. Fail on any critical issue.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    pdf_bytes = pdf_path.read_bytes()

    # Step 1: Run extraction pipeline
    import asyncio
    payload = asyncio.run(extract(pdf_bytes))
    extracted_json = payload.model_dump(mode="json")

    # Step 2: Run judge
    judge_result = run_judge(pdf_bytes, extracted_json)

    # Step 3: Record metadata for HTML report
    record_property("pdf_file", pdf_path.name)
    record_property("metrics_in_pdf", judge_result.total_metrics_in_pdf)
    record_property("metrics_extracted", judge_result.total_metrics_extracted)
    record_property(
        "coverage",
        f"{judge_result.total_metrics_extracted}/{judge_result.total_metrics_pdf}"
        if judge_result.total_metrics_in_pdf > 0
        else "N/A",
    )

    critical_issues = [i for i in judge_result.issues if i.severity == "critical"]
    warnings = [i for i in judge_result.issues if i.severity == "warning"]

    # Record all issues in report
    for idx, issue in enumerate(judge_result.issues):
        record_property(
            f"issue_{idx + 1}",
            f"[{issue.severity.upper()}] {issue.metric or '?'}.{issue.field or '?'}: "
            f"expected={issue.expected!r} got={issue.got!r} — {issue.description}",
        )

    # Fail on critical issues
    if critical_issues:
        details = "\n".join(
            f"  - [{i.metric}] {i.field}: expected={i.expected!r} got={i.got!r} — {i.description}"
            for i in critical_issues
        )
        pytest.fail(
            f"{pdf_path.name}: {len(critical_issues)} critical issue(s) found:\n{details}\n"
            f"({len(warnings)} warning(s) — see HTML report for details)"
        )
```

**Step 2: Add a README to fixtures/**

```
# backend/tests/accuracy/fixtures/README.md
Place anonymized PDF lab reports here.
These files are used by test_accuracy.py for end-to-end extraction validation.
Do NOT commit real patient data.
```

**Step 3: Verify test collects correctly (no PDFs needed yet)**

```bash
cd backend && python -m pytest tests/accuracy/test_accuracy.py --collect-only
```
Expected output:
```
collected 0 items
no tests ran
```
(Zero items is correct — no PDFs in fixtures/ yet.)

**Step 4: Commit**

```bash
git add backend/tests/accuracy/test_accuracy.py backend/tests/accuracy/fixtures/README.md
git commit -m "feat: add end-to-end PDF accuracy test with LLM judge"
```

---

### Task 6: Add a fixture PDF and run end-to-end

**Files:**
- Add: `backend/tests/accuracy/fixtures/sample_01.pdf` (you provide this)

**Step 1: Copy a real PDF into fixtures/**

Place an anonymized PDF lab report at:
```
backend/tests/accuracy/fixtures/sample_01.pdf
```

**Step 2: Set OPENAI_API_KEY**

```bash
export OPENAI_API_KEY=sk-...
```
Or create `backend/.env` with `OPENAI_API_KEY=sk-...` and load it.

**Step 3: Run the test with HTML report**

```bash
cd backend && python -m pytest tests/accuracy/test_accuracy.py -v \
    --html=tests/accuracy/report.html --self-contained-html
```

Expected terminal output (if extraction is correct):
```
tests/accuracy/test_accuracy.py::test_accuracy[sample_01.pdf] PASSED
```

Expected terminal output (if issues found):
```
tests/accuracy/test_accuracy.py::test_accuracy[sample_01.pdf] FAILED
  - [GLUCOSA] value_numeric: expected='94.5' got='94.2' — Value differs by >1%
```

**Step 4: Open the HTML report in browser**

```
backend/tests/accuracy/report.html
```
Open in any browser. You'll see a table with per-test metadata: PDF name, metrics count, all issues listed.

**Step 5: Add PDFs to .gitignore (if they contain patient data)**

In `backend/tests/accuracy/fixtures/`, create `.gitignore`:
```
*.pdf
```

**Step 6: Commit**

```bash
git add backend/tests/accuracy/fixtures/.gitignore
git commit -m "chore: gitignore PDF fixtures to prevent committing patient data"
```

---

## Running All PDFs

```bash
# All PDFs at once with HTML report:
cd backend && python -m pytest tests/accuracy/ -v \
    --html=tests/accuracy/report.html --self-contained-html

# Single PDF:
cd backend && python -m pytest tests/accuracy/ -v -k "sample_01"

# Skip accuracy tests in regular CI (they cost API tokens):
cd backend && python -m pytest tests/ --ignore=tests/accuracy/
```

## Cost Estimate

~2 OpenAI API calls per PDF (extraction + judge). Using gpt-4o for judge (~$0.01–0.05 per PDF at typical lab report size).
