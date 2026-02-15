from __future__ import annotations

import asyncio
import os
from typing import Any

from openai import AsyncOpenAI

from backend.v2.prompts import EXTRACT_SYSTEM_PROMPT
from backend.v2.schemas import ImportV2

_client: AsyncOpenAI | None = None
DEFAULT_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_TIMEOUT_SEC = 300.0


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
    return _client


async def extract_import_v2_from_pdf_bytes(pdf_bytes: bytes) -> dict[str, Any]:
    max_file_size_bytes = int(os.getenv("OPENAI_MAX_FILE_SIZE_BYTES", str(DEFAULT_MAX_FILE_SIZE_BYTES)))
    if len(pdf_bytes) > max_file_size_bytes:
        raise ValueError(f"PDF exceeds max allowed size: {max_file_size_bytes} bytes")

    timeout_sec = float(os.getenv("OPENAI_EXTRACT_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))
    client = get_client()

    file_purpose = os.getenv("OPENAI_FILE_PURPOSE", "assistants")
    uploaded_file = None

    try:
        uploaded_file = await asyncio.wait_for(
            client.files.create(
                file=("report.pdf", pdf_bytes, "application/pdf"),
                purpose=file_purpose,
            ),
            timeout=timeout_sec,
        )

        response = await asyncio.wait_for(
            client.responses.parse(
                model="gpt-5.2",
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": EXTRACT_SYSTEM_PROMPT}]},
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Extract the report into ImportV2 JSON."},
                            {"type": "input_file", "file_id": uploaded_file.id},
                        ],
                    },
                ],
                text_format=ImportV2,
            ),
            timeout=timeout_sec,
        )

        parsed = response.output_parsed
        if isinstance(parsed, ImportV2):
            return parsed.model_dump(mode="json")
        if isinstance(parsed, dict):
            return parsed
        return ImportV2.model_validate(parsed).model_dump(mode="json")
    finally:
        if uploaded_file is not None:
            try:
                await client.files.delete(uploaded_file.id)
            except Exception:
                pass
