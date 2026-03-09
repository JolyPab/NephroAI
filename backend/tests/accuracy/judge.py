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
    """Upload the PDF and extracted JSON to GPT and ask it to audit the extraction."""
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
