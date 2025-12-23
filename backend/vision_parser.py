"""Vision-based PDF parser using OpenAI GPT-4o with structured outputs."""

import base64
import io
import os
from typing import List, Dict, Any

import fitz  # PyMuPDF
from PIL import Image
from openai import OpenAI

from models import ImportJson, ImportedLabItem


SYSTEM_PROMPT = (
    "Ты — медицинский эксперт. Задача: извлечь анализы, даты и референсы. "
    "Шаги: 1) Найди дату регистрации/выдачи ('FECHA DE REGISTRO', 'FECHA DE LIBERACION' и т.п.). "
    "Если дата найдена, ставь её в taken_at всех записей в формате YYYY-MM-DD. Если даты нет, taken_at=null. "
    "2) Извлеки метрики: name, value/value_text, unit, ref_range, ref_min/ref_max. "
    "Для '> 90' ставь ref_min=90, ref_max=null. Для '0.0 a 2.5' ставь ref_min=0, ref_max=2.5. "
    "Игнорируй технические числа из юнитов (например, 1.73 в 'mL/min/1.73m2') при заполнении ref_min/ref_max. "
    "Не создавай отдельные записи для заголовков; ищи число ниже и объединяй. "
    "Если нет числового или бинарного значения (0/1), не включай запись."
)


def _extract_page_text_and_images(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Extract text and embedded images per page as base64 strings, with size filtering and compression."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[Dict[str, Any]] = []

    try:
        for page in doc:
            page_text = page.get_text("text") or ""
            page_images: List[str] = []

            for img in page.get_images(full=True):
                xref = img[0]
                extracted = doc.extract_image(xref)
                img_bytes = extracted.get("image", b"")
                if not img_bytes:
                    continue
                # Skip tiny images (<10KB) to avoid noise
                if len(img_bytes) < 10 * 1024:
                    continue

                # Compress with Pillow: JPEG, quality 70, max dimension 1024px
                try:
                    with Image.open(io.BytesIO(img_bytes)) as im:
                        im = im.convert("RGB")
                        im.thumbnail((1024, 1024))
                        buf = io.BytesIO()
                        im.save(buf, format="JPEG", quality=70, optimize=True)
                        img_bytes = buf.getvalue()
                except Exception:
                    # If Pillow fails, fall back to original bytes
                    pass

                page_images.append(base64.b64encode(img_bytes).decode("ascii"))

            pages.append({"text": page_text, "images": page_images})
    finally:
        doc.close()

    return pages


def _postprocess_item(item: ImportedLabItem) -> ImportedLabItem:
    # 1. Clean references
    ref_range = getattr(item, "ref_range", None)
    if ref_range in [None, "None", "null", "N/A"]:
        ref_range = ""

    # 2. Handle value/value_text as a unified string
    raw_val = item.value if item.value is not None else item.value_text
    val = str(raw_val).strip().lower() if raw_val is not None else ""

    notes = item.notes
    value_out = item.value
    value_text_out = item.value_text
    # Normalize ref_min/ref_max as floats if present
    def _to_float(v):
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            try:
                return float(str(v).replace(",", "."))
            except Exception:
                return None

    ref_min = _to_float(getattr(item, "ref_min", None))
    ref_max = _to_float(getattr(item, "ref_max", None))

    # Binary logic
    if "negativo" in val:
        value_out = 0.0
        value_text_out = None
    elif "positivo" in val:
        value_out = 1.0
        value_text_out = None
    else:
        try:
            value_out = float(val.replace(",", ".")) if val else None
            value_text_out = None
        except ValueError:
            if val and val not in ["none", "null", "nan"]:
                notes = f"{notes or ''} Result: {val}".strip()
            value_out = None
            value_text_out = None

    return item.copy(
        update={
            "value": value_out,
            "value_text": value_text_out,
            "notes": notes,
            "ref_range": ref_range,
            "ref_min": ref_min,
            "ref_max": ref_max,
        }
    )


def parse_pdf_vision(pdf_bytes: bytes) -> ImportJson:
    """
    Parse PDF bytes using GPT-4o vision with structured outputs.

    Hybrid approach: use text layer for speed and send embedded images alongside for completeness.
    Processes each page separately to stay under token limits on large files.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"), timeout=60.0)

    pages = _extract_page_text_and_images(pdf_bytes)
    if not pages:
        raise ValueError("PDF has no readable content")

    aggregated_items = []
    patient_id = None
    source_pdf = None
    normalization_method = None

    for idx, page in enumerate(pages):
        text = page.get("text", "")
        images = page.get("images", [])

        if not text.strip() and not images:
            continue

        print(f"--- Обработка страницы {idx + 1}... ---")

        user_content: List[dict] = []
        if text.strip():
            user_content.append(
                {"type": "text", "text": f"Page {idx + 1} text:\n{text}"}
            )

        for img_b64 in images:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                }
            )

        # Choose model: vision for pages with images, mini for text-only
        model_default = "gpt-4o" if images else "gpt-4o-mini"
        model_name = (
            os.getenv("OPENAI_MODEL", model_default)
            if images
            else os.getenv("OPENAI_MODEL_TEXT", model_default)
        )

        completion = client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=ImportJson,
        )

        parsed = completion.choices[0].message.parsed
        if patient_id is None:
            patient_id = parsed.patient_id
        if source_pdf is None:
            source_pdf = parsed.source_pdf
        if normalization_method is None:
            normalization_method = parsed.normalization_method

        aggregated_items.extend(parsed.items or [])

    if not aggregated_items:
        raise ValueError("PDF has no readable content")

    cleaned_items = []
    for it in aggregated_items:
        processed = _postprocess_item(it)
        # Keep only if numeric/binary value or meaningful notes
        has_value = processed.value is not None
        has_notes = bool(processed.notes and processed.notes.strip())

        if has_value or has_notes:
            cleaned_items.append(processed)

    return ImportJson(
        patient_id=patient_id or "unknown",
        items=cleaned_items,
        source_pdf=source_pdf,
        normalization_method=normalization_method,
    )
