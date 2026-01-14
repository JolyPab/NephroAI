"""LLM-based normalization using AITunnel."""

import json
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.pdf_structures import RawRow
from backend.models import ImportedLabItem
from backend.llm_config import (
    get_llm_client, 
    get_llm_model, 
    get_batch_size, 
    get_max_workers,
    get_request_timeout,
    get_max_retries
)


# System prompt for the LLM
SYSTEM_PROMPT = """Ты — парсер медицинских лабораторных отчётов.

Тебе дают список строк из PDF (каждая строка — это одна строка таблицы или текста).

Твоя задача:
1. Найти строки, которые описывают результаты анализов.
2. Собрать их в структурированный JSON:
   - НЕ ПРИДУМЫВАТЬ значения, которых нет в строках
   - НЕ ИЗМЕНЯТЬ числа, только при необходимости заменять запятую на точку
   - Если анализ занимает несколько строк (название отдельно, результат отдельно) — объединить их
   - Для каждого анализа указать source_rows — индексы строк, из которых взята информация
3. Отдельно собрать базовые метаданные пациента (если есть): имя, номер услуги, возраст, пол.
4. Любые строки, которые не являются ни анализами, ни метаданными (футер, юридический текст, номера страниц, методы анализа), поместить в ignored_rows.

ОБРАБОТКА СКЛЕЕННЫХ СЛОВ:
- Названия анализов часто склеены без пробелов: SODIOSERICO, COLESTEROLDEALTADENSIDAD, TASADEFILTRACIONGLOMERULAR
- ОБЯЗАТЕЛЬНО раздели их на читаемые слова: SODIO SERICO, COLESTEROL DE ALTA DENSIDAD, TASA DE FILTRACION GLOMERULAR
- Референс-диапазоны тоже могут быть склеены: "100a200" -> "100 a 200", "0.5a3.0" -> "0.5 a 3.0"
- Используй контекст и знания испанской медицинской терминологии для правильного разделения
- Общие паттерны:
  * XXXSERICO -> XXX SERICO (электролиты)
  * XXXDEYYY -> XXX DE YYY (связки с "de")
  * XXXYYY где XXX и YYY - разные слова -> XXX YYY
  * TASADE -> TASA DE
  * RELACIONXXX -> RELACION XXX
  * COEFICIENTE -> COEFICIENTE (раздели если склеено)

КРИТИЧЕСКИ ВАЖНО:
- Обязательно верни ответ СТРОГО в формате валидного JSON с ключами: analytes, metadata, ignored_rows
- НЕЛЬЗЯ добавлять текст до или после JSON
- Если не уверен в каком-то поле — ставь null и сохраняй оригинальный текст
- НЕ ПРИДУМЫВАЙ анализы, которых нет в строках
- НЕ ПРИДУМЫВАЙ числовые значения и референс-диапазоны
- ВСЕГДА разделяй склеенные слова в названиях и референс-диапазонах

Формат ответа:
{
  "analytes": [
    {
      "analyte_name": "SODIO SERICO",  // ВАЖНО: раздели склеенные слова!
      "original_name": "SODIOSERICO",  // оригинал из PDF
      "value": 137.8,
      "value_text": null,  // текстовое значение если value=null (например "NEGATIVO")
      "unit": "mmol/L",
      "ref_range": "136 a 145",  // ВАЖНО: раздели "136a145" на "136 a 145"
      "section": null,  // название секции если есть
      "source_rows": [7, 8]  // индексы строк row_index
    },
    {
      "analyte_name": "COLESTEROL DE ALTA DENSIDAD",  // раздели COLESTEROLDEALTADENSIDAD
      "original_name": "COLESTEROLDEALTADENSIDAD",
      "value": 36.0,
      "unit": "mg/dL",
      "ref_range": "40 a 60",  // раздели "40a60"
      "section": null,
      "source_rows": [15]
    }
  ],
  "metadata": {
    "patient_name": "YAMID ENRIQUE PICO LOPEZ",
    "service_number": "13231840002",
    "age": "46",
    "sex": "MASCULINO"
  },
  "ignored_rows": [0, 1, 2, 5, 6]
}"""


def convert_rows_to_simple_format(rows: List[RawRow]) -> List[Dict[str, Any]]:
    """Convert RawRow objects to simple dict format for LLM."""
    result = []
    
    for i, row in enumerate(rows):
        # Combine all cells into one text string
        text = ' '.join(cell.text for cell in row.cells if cell.text.strip())
        
        result.append({
            "page": row.page,
            "row_index": i,  # Use index in the batch
            "text": text
        })
    
    return result


def create_batch_prompt(rows_batch: List[RawRow]) -> str:
    """Create user prompt for a batch of rows."""
    simple_rows = convert_rows_to_simple_format(rows_batch)
    return json.dumps({"rows": simple_rows}, ensure_ascii=False, indent=2)


def validate_llm_response(response_data: Dict[str, Any]) -> bool:
    """Validate that LLM response has correct structure."""
    if not isinstance(response_data, dict):
        return False
    
    # Must have analytes array
    if "analytes" not in response_data or not isinstance(response_data["analytes"], list):
        return False
    
    # Validate each analyte
    for analyte in response_data["analytes"]:
        if not isinstance(analyte, dict):
            return False
        
        # Required fields
        if "analyte_name" not in analyte:
            return False
        
        # source_rows should be present
        if "source_rows" not in analyte or not isinstance(analyte["source_rows"], list):
            return False
    
    return True


def parse_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse LLM response text as JSON.
    
    Handles cases where LLM might add markdown code blocks or extra text.
    """
    # Try direct JSON parsing first
    try:
        data = json.loads(response_text)
        if validate_llm_response(data):
            return data
    except json.JSONDecodeError:
        pass
    
    # Try extracting JSON from markdown code block
    if "```json" in response_text:
        try:
            start = response_text.index("```json") + 7
            end = response_text.index("```", start)
            json_text = response_text[start:end].strip()
            data = json.loads(json_text)
            if validate_llm_response(data):
                return data
        except (ValueError, json.JSONDecodeError):
            pass
    
    # Try extracting anything between { and }
    try:
        start = response_text.index("{")
        end = response_text.rindex("}") + 1
        json_text = response_text[start:end]
        data = json.loads(json_text)
        if validate_llm_response(data):
            return data
    except (ValueError, json.JSONDecodeError):
        pass
    
    return None


def call_llm_for_batch(client, model: str, rows_batch: List[RawRow], timeout: Optional[int] = None, max_retries: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Call LLM to normalize a batch of rows with retry logic and timeout.
    
    Args:
        client: OpenAI client
        model: Model name
        rows_batch: Batch of rows to process
        timeout: Request timeout in seconds (default: from config)
        max_retries: Maximum number of retry attempts (default: from config)
    
    Returns:
        Parsed JSON or None on failure.
    """
    if timeout is None:
        timeout = get_request_timeout()
    if max_retries is None:
        max_retries = get_max_retries()
    
    user_prompt = create_batch_prompt(rows_batch)
    total_start_time = time.time()
    
    for attempt in range(max_retries + 1):
        try:
            attempt_start_time = time.time()
            
            # Call AITunnel API (OpenAI-compatible) with timeout
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},  # Request structured JSON
                temperature=0.1,  # Low temperature for consistency
                timeout=timeout,  # Request timeout
            )
            
            elapsed = time.time() - attempt_start_time
            response_text = response.choices[0].message.content
            
            # Parse and validate
            parsed = parse_llm_response(response_text)
            if parsed:
                return parsed
            else:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s...
                    total_elapsed = time.time() - total_start_time
                    print(f"Warning: Failed to parse LLM response (attempt {attempt + 1}/{max_retries + 1}, {total_elapsed:.2f}s), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    total_elapsed = time.time() - total_start_time
                    print(f"Warning: Failed to parse LLM response for batch of {len(rows_batch)} rows after {max_retries + 1} attempts ({total_elapsed:.2f}s)")
                    return None
                
        except Exception as e:
            elapsed = time.time() - attempt_start_time
            total_elapsed = time.time() - total_start_time
            error_msg = str(e)
            
            # Check if it's a timeout or network error (retry-able)
            is_retryable = any(keyword in error_msg.lower() for keyword in ['timeout', 'connection', 'network', 'rate limit', '429'])
            
            if attempt < max_retries and is_retryable:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Error calling LLM (attempt {attempt + 1}/{max_retries + 1}): {error_msg[:100]}")
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"Error calling LLM for batch after {attempt + 1} attempts: {error_msg[:200]}")
                print(f"Request took {elapsed:.2f}s (total {total_elapsed:.2f}s) before failure")
                return None
    
    return None


def llm_analyte_to_imported_item(llm_analyte: Dict[str, Any], extracted_date: Optional[datetime] = None) -> ImportedLabItem:
    """
    Convert LLM analyte dict to ImportedLabItem.
    
    Args:
        llm_analyte: Dictionary from LLM response with analyte data
        extracted_date: Optional datetime extracted from PDF header
    """
    # Extract fields with defaults
    analyte_name = llm_analyte.get("analyte_name", "").strip().upper()
    original_name = llm_analyte.get("original_name", "").strip()
    
    # Handle value (numeric or text)
    value = llm_analyte.get("value")
    value_text = llm_analyte.get("value_text")
    
    # If value is string, try to parse as float
    if isinstance(value, str):
        try:
            value = float(value.replace(',', '.'))
            value_text = None
        except ValueError:
            value_text = value
            value = None
    
    unit = llm_analyte.get("unit")
    if unit and not unit.strip():
        unit = None
    
    ref_range = llm_analyte.get("ref_range")
    if ref_range and not ref_range.strip():
        ref_range = None
    
    return ImportedLabItem(
        analyte_name=analyte_name,
        original_name=original_name if original_name else None,
        value=value,
        value_text=value_text,
        unit=unit,
        material=None,
        taken_at=extracted_date,  # Use extracted date from PDF
        ref_range=ref_range
    )


def normalize_with_llm(rows: List[RawRow], extracted_date: Optional[datetime] = None, max_workers: Optional[int] = None) -> Optional[List[ImportedLabItem]]:
    """
    Normalize PDF rows using LLM with parallel batch processing.
    
    Args:
        rows: List of RawRow objects from PDF extraction
        extracted_date: Optional datetime extracted from PDF header
        max_workers: Maximum number of parallel workers (default: min(5, batch_count))
        
    Returns:
        List of ImportedLabItem if successful, None if LLM fails
    """
    client = get_llm_client()
    if not client:
        return None
    
    model = get_llm_model()
    batch_size = get_batch_size()
    
    # Split rows into batches with overlap to preserve context
    # Overlap ensures multi-line analytes aren't split across batches
    # This is critical for medical data accuracy
    overlap_size = min(10, batch_size // 5)  # 10 rows or 20% of batch size, whichever is smaller
    batches = []
    
    i = 0
    while i < len(rows):
        batch_end = min(i + batch_size, len(rows))
        batch = rows[i:batch_end]
        batches.append(batch)
        
        # Move to next batch with overlap (unless it's the last batch)
        if batch_end < len(rows):
            i = batch_end - overlap_size  # Start next batch with overlap
        else:
            break
    
    batch_count = len(batches)
    
    if overlap_size > 0:
        print(f"Using batch overlap of {overlap_size} rows to preserve context between batches")
    
    # Determine optimal number of workers (but not too many to avoid rate limits)
    if max_workers is None:
        max_workers = get_max_workers()
    
    # Cap max_workers to batch_count
    max_workers = min(max_workers, batch_count)
    
    print(f"Using LLM normalization with model: {model}")
    print(f"Processing {len(rows)} rows in {batch_count} batches of ~{batch_size} rows")
    print(f"Using {max_workers} parallel workers")
    print(f"Request timeout: {get_request_timeout()}s, Max retries: {get_max_retries()}")
    
    start_time = time.time()
    all_analytes = []
    all_metadata = {}
    successful_batches = 0
    failed_batches = 0
    
    # Process batches in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batch processing tasks
        future_to_batch = {
            executor.submit(call_llm_for_batch, client, model, batch): (batch_idx + 1, batch)
            for batch_idx, batch in enumerate(batches)
        }
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_batch):
            batch_num, batch = future_to_batch[future]
            batch_start = time.time()
            
            try:
                result = future.result()
                batch_elapsed = time.time() - batch_start
                
                if result:
                    successful_batches += 1
                    # Extract analytes
                    for llm_analyte in result.get("analytes", []):
                        try:
                            item = llm_analyte_to_imported_item(llm_analyte, extracted_date=extracted_date)
                            all_analytes.append(item)
                        except Exception as e:
                            print(f"Warning: Failed to convert analyte in batch {batch_num}: {e}")
                            continue
                    
                    # Merge metadata (prefer non-null values)
                    metadata = result.get("metadata", {})
                    for key, value in metadata.items():
                        if value and (key not in all_metadata or not all_metadata[key]):
                            all_metadata[key] = value
                    
                    print(f"✓ Batch {batch_num}/{batch_count} completed ({len(batch)} rows, {batch_elapsed:.2f}s)")
                else:
                    failed_batches += 1
                    batch_elapsed = time.time() - batch_start
                    print(f"✗ Batch {batch_num}/{batch_count} failed ({len(batch)} rows, {batch_elapsed:.2f}s)")
                    
            except Exception as e:
                failed_batches += 1
                batch_elapsed = time.time() - batch_start
                print(f"✗ Batch {batch_num}/{batch_count} error: {e} ({batch_elapsed:.2f}s)")
    
    total_elapsed = time.time() - start_time
    
    if not all_analytes:
        print(f"Warning: LLM produced no analytes after {total_elapsed:.2f}s, falling back to rule-based normalizer")
        return None
    
    # Deduplicate analytes (from overlap between batches)
    # Prefer analytes with more complete information
    deduplicated = {}
    for item in all_analytes:
        key = item.analyte_name.upper().strip()
        
        # If we haven't seen this analyte, add it
        if key not in deduplicated:
            deduplicated[key] = item
        else:
            # If we have a duplicate, prefer the one with more information
            existing = deduplicated[key]
            
            # Prefer item with non-null value over null
            if existing.value is None and item.value is not None:
                deduplicated[key] = item
            # Prefer item with ref_range over without
            elif not existing.ref_range and item.ref_range:
                deduplicated[key] = item
            # Prefer item with unit over without
            elif not existing.unit and item.unit:
                deduplicated[key] = item
    
    unique_analytes = list(deduplicated.values())
    
    if len(all_analytes) != len(unique_analytes):
        print(f"Note: Deduplicated {len(all_analytes)} -> {len(unique_analytes)} unique analytes (from batch overlap)")
    
    print(f"\n{'='*60}")
    print(f"LLM normalization complete:")
    print(f"  ✓ Successful batches: {successful_batches}/{batch_count}")
    print(f"  ✗ Failed batches: {failed_batches}/{batch_count}")
    print(f"  📊 Total analytes extracted: {len(unique_analytes)} (deduplicated from {len(all_analytes)})")
    print(f"  ⏱️  Total time: {total_elapsed:.2f}s ({total_elapsed/60:.1f} min)")
    print(f"  📈 Speed: {len(rows)/total_elapsed:.1f} rows/sec")
    print(f"{'='*60}")
    
    if all_metadata:
        print(f"Extracted metadata: {all_metadata}")
    
    return unique_analytes
