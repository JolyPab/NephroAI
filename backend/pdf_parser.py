"""PDF text extraction and parsing for lab reports."""

import io
import re
from typing import List, Optional, Union
from datetime import datetime
import fitz  # PyMuPDF
import pdfplumber

from models import ImportedLabItem, ImportJson

# New refactored pipeline
from pdf_extractor import (
    extract_rows_from_pdf,
    NoTextLayerError as ExtractorNoTextLayerError,
    RawRow,
)
from analyte_mapper import build_raw_analytes
from analyte_normalizer import normalize_analytes

# Optional LLM-based normalization
from llm_config import is_llm_enabled
from llm_normalizer import normalize_with_llm


# ---------------------------------------------------------------------------
# Простой regex‑парсер (по мотивам KA.basic_regex_extract)
# ---------------------------------------------------------------------------

_BASIC_ANALYTE_ROW = re.compile(
    r"""
    ^\s*                                   # начало строки
    (?P<name>[A-ZÁÉÍÓÚÑ/ \-\.\(\)0-9]+?)   # имя аналита
    \s{1,}                                 # хотя бы один пробел
    (?P<value>[<>\=\~]?\s*\d+(?:[.,]\d+)?) # число (с возможным > / <)
    \s{0,}
    (?P<unit>(
        mg/dL|g/dL|mmol/L|UI/L|U/L|ng/mL|µg/dL|ug/dL|mg/L|
        mL/min/1\.73m2|mL/min|%|fL|pg|gr/dL|Cel./µL|U/l
    ))?
    \b
    """,
    re.VERBOSE | re.IGNORECASE | re.MULTILINE,
)

_BASIC_RANGE_HINT = re.compile(
    r"(VALORES?\s+DE\s+REFERENCIA.*?$|"
    r"[<>\=\~]?\s*\d+(?:[.,]\d+)?\s*a\s*[<>\=\~]?\s*\d+(?:[.,]\d+)?"
    r"(?:\s*\w+)?(?:\s*[A-Za-zÁÉÍÓÚÑ]+)?)",
    re.IGNORECASE | re.MULTILINE,
)


def basic_regex_extract_to_items(
    text: str, extracted_date: Optional[datetime] = None
) -> List[ImportedLabItem]:
    """
    Простой офлайновый парсер: ищет строки вида
    'NOMBRE 94.2 mg/dL' и пытается вытащить имя, значение, единицу и диапазон.
    """
    items: List[ImportedLabItem] = []
    lines = text.splitlines()

    # Небольшое "окно" последних строк, чтобы искать там ref_range
    window: List[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            window = []
            continue

        window.append(line)
        if len(window) > 4:
            window.pop(0)

        m = _BASIC_ANALYTE_ROW.search(line)
        if not m:
            continue

        name = " ".join(m.group("name").split())
        value_str = m.group("value").replace(" ", "")
        unit = m.group("unit")
        ref_range = None

        # Если "имя" выглядит как число (или очень короткий мусор),
        # попробуем взять в качестве имени предыдущую осмысленную строку.
        if re.fullmatch(r"[<>~=]?\s*\d+(?:[.,]\d+)?", name) or len(name) < 3:
            for prev in reversed(window[:-1]):  # исключаем текущую строку
                prev_clean = prev.strip()
                # Должны быть буквы и не слишком много цифр
                if not re.search(r"[A-Za-zÁÉÍÓÚÑ]", prev_clean):
                    continue
                if sum(c.isdigit() for c in prev_clean) > len(prev_clean) * 0.3:
                    continue
                # Это, скорее всего, название анализа
                name = " ".join(prev_clean.split())
                break

        # Ищем подсказку диапазона в соседних строках
        for w in window:
            if w == line:
                continue
            rr = _BASIC_RANGE_HINT.search(w)
            if rr:
                ref_range = rr.group(0)
                break

        # Пробуем распарсить значение
        value: Optional[float] = None
        value_text: Optional[str] = None
        try:
            value = float(value_str.replace(",", "."))
        except ValueError:
            value_text = value_str

        items.append(
            ImportedLabItem(
                analyte_name=name.upper(),
                value=value,
                value_text=value_text,
                unit=unit,
                material=None,
                taken_at=extracted_date,
                ref_range=ref_range,
            )
        )

    return items


class NoTextLayerError(Exception):
    """Raised when PDF has no text layer."""
    pass


def extract_date_from_pdf(rows: List[RawRow]) -> Optional[datetime]:
    """
    Extract date from PDF header (first 30 rows).
    
    Looks for common date patterns in Spanish lab reports:
    - "FECHA: 01/01/2024"
    - "Fecha de extracción: 01-01-2024"
    - "Fecha de toma: 2024-01-01"
    - "01/01/2024"
    - "01-01-2024"
    - "2024-01-01"
    
    Args:
        rows: List of RawRow objects from PDF
        
    Returns:
        datetime object if date found, None otherwise
    """
    # Look at first 30 rows (usually in header area)
    header_rows = rows[:30] if len(rows) > 30 else rows
    
    # Collect all text from header rows
    header_text = " ".join(
        " ".join(cell.text for cell in row.cells)
        for row in header_rows
    ).upper()
    
    # Common date keywords in Spanish
    date_keywords = [
        r'FECHA[:\s]+',
        r'FECHA\s+DE\s+(?:EXTRACCION|TOMA|MUESTRA|ANALISIS|LABORATORIO)[:\s]+',
        r'FECHA\s+DE\s+RECEPCION[:\s]+',
        r'FECHA\s+DEL\s+EXAMEN[:\s]+',
    ]
    
    # Date patterns: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD.MM.YYYY
    date_patterns = [
        r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})',  # YYYY-MM-DD
    ]
    
    # Try to find date with keyword
    for keyword in date_keywords:
        for pattern in date_patterns:
            full_pattern = keyword + pattern
            match = re.search(full_pattern, header_text, re.IGNORECASE)
            if match:
                try:
                    if len(match.group(1)) == 4:  # YYYY-MM-DD format
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    else:  # DD/MM/YYYY format
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    
                    # Validate date
                    if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
    
    # Try to find standalone date (without keyword) - more restrictive
    # Look for dates that look like lab report dates (usually in first 10 rows)
    first_10_rows = rows[:10] if len(rows) > 10 else rows
    first_text = " ".join(
        " ".join(cell.text for cell in row.cells)
        for row in first_10_rows
    )
    
    for pattern in date_patterns:
        matches = list(re.finditer(pattern, first_text))
        if matches:
            # Take the first reasonable date
            for match in matches:
                try:
                    if len(match.group(1)) == 4:  # YYYY-MM-DD format
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    else:  # DD/MM/YYYY format
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    
                    # Validate date (more strict for standalone dates)
                    if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
    
    return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF using PyMuPDF first, then pdfplumber as fallback.
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        ValueError: If PDF is empty or invalid
        NoTextLayerError: If no text layer is found in PDF
    """
    if not pdf_bytes or len(pdf_bytes) < 100:  # Basic check for valid PDF
        raise ValueError("Empty or invalid PDF file")
    
    # Try PyMuPDF first
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text("text")
            if page_text:
                text_parts.append(page_text)
        doc.close()
        
        full_text = "\n".join(text_parts)
        if full_text.strip():
            return full_text
    except Exception as e:
        # PyMuPDF failed, try pdfplumber
        pass
    
    # Fallback to pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            full_text = "\n".join(text_parts)
            if full_text.strip():
                return full_text
    except Exception as e:
        pass
    
    # No text found
    raise NoTextLayerError("No text layer found in PDF. PDF appears to be image-based.")


def parse_lab_results(text: str) -> List[ImportedLabItem]:
    """
    Parse lab test results from extracted text.
    
    This function looks for patterns like:
    - "Glucosa 94.2 mg/dL 70 a 100"
    - "Urea 74.8 mg/dL 19 a 44"
    - "Relacion BUN/CRE 14.75 10 a 20"
    - "Colesterol No Hdl 160 mg/dL" (no ref range)
    - "RELACIÓN BUN/CRE" followed by "Relacion BUN/CRE 14.75 10 a 20"
    
    Args:
        text: Extracted text from PDF
        
    Returns:
        List of ImportedLabItem objects
    """
    items = []
    processed_analyte_names = set()  # Track processed analyte names (case-insensitive)
    
    # Words to exclude as analyte names (common Spanish words and junk)
    excluded_words = {
        'de', 'a', 'y', 'en', 'el', 'la', 'los', 'las', 'un', 'una', 'por', 'con',
        'para', 'que', 'es', 'son', 'del', 'al', 'le', 'se', 'lo', 'no', 'si',
        'o', 'ni', 'como', 'mas', 'pero', 'sin', 'sobre', 'entre', 'hasta',
        'desde', 'hacia', 'según', 'durante', 'mediante', 'excepto', 'salvo',
        'resultados', 'unidades', 'valores', 'referencia', 'nota', 'metodo',
        'muestra', 'analitica', 'pag', 'página'
    }

    # Keywords that typically appear in interpretation tables rather than results
    interpretation_keywords = {
        'estadio', 'riesgo', 'disminuida', 'disminuido', 'moderado', 'moderada',
        'moderadamente', 'leve', 'levemente', 'optimo', 'óptimo', 'limite', 'límite'
    }
    
    # Common units that shouldn't be mistaken for analyte names
    common_units = {
        'mg/dl', 'mg/l', 'mmol/l', 'u/l', 'ng/ml', 'μg/dl', 'μg/dl', 'pg/ml',
        'ml/min', 'ml/min/1.73m2', 'g/dl', 'gr/dl', 'mg/l', 'iu/l', 'mcg/dl'
    }
    
    def is_valid_analyte_name(name: str) -> bool:
        """Check if analyte name is valid (not junk)."""
        name_lower = name.lower().strip()
        
        # Must be at least 3 characters (allow for short names like "pH", "Na")
        if len(name_lower) < 2:
            return False
        
        # Exclude if it's a single excluded word
        if name_lower in excluded_words:
            return False
        
        # Exclude if it's just a unit
        if name_lower in common_units:
            return False
        
        # Exclude if it's mostly numbers or special characters
        if re.match(r'^[\d\s\-\.]+$', name_lower):
            return False
        
        # Exclude if it contains too many numbers (likely not a name)
        digit_count = sum(1 for c in name_lower if c.isdigit())
        if digit_count > len(name_lower) * 0.3 and len(name_lower) < 10:
            return False

        # Exclude if it ends abruptly (common in wrapped headings)
        if name_lower.endswith(' de'):
            return False

        # Exclude interpretation keywords unless it's the actual TFG measurement
        if any(keyword in name_lower for keyword in interpretation_keywords):
            if 'filtracion' not in name_lower and 'glomerular' not in name_lower:
                return False
        
        # Must contain at least one letter
        if not re.search(r'[a-záéíóúñüç]', name_lower, re.IGNORECASE):
            return False
        
        return True
    
    # Normalize text: keep line breaks for better parsing, but normalize spaces
    # Don't collapse all whitespace - preserve structure
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs -> single space
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines -> double newline
    
    # Pattern for ratio/index without unit (like BUN/CRE) - HIGHEST PRIORITY
    # Matches: "RELACION BUN/CRE 14.75 10 a 20" or "Relacion BUN/CRE 14.75 10 a 20"
    # Very strict: ratio must be uppercase letters separated by /, and cannot be a unit
    pattern_ratio = re.compile(
        r'\b(REL[A-ZÁÉÍÓÚÑÜ]*\s+)([A-Z]{2,}/[A-Z]{2,})\s+'  # Must have "REL" prefix, ratio must be 2+ uppercase letters
        r'([\d,\.]+)\s*'  # Value (can have comma or dot)
        r'([\d,\.]+\s*(?:a|a|–|-|to)\s*[\d,\.]+)?',  # Ref range (optional)
        re.IGNORECASE
    )
    
    # First pass: handle ratios (BUN/CRE, etc.) - MUST BE FIRST to catch them before standard pattern
    for match in pattern_ratio.finditer(text):
        ratio_name = match.group(2)  # The actual ratio (BUN/CRE)
        relacion_prefix = match.group(1) or ""
        
        # Build full name: "RELACION BUN/CRE"
        analyte_name = (relacion_prefix + ratio_name).strip()
        
        # Normalize: handle spaces, capitalize properly
        analyte_name = re.sub(r'\s+', ' ', analyte_name).strip()
        analyte_name_lower = analyte_name.lower()
        
        # Validate and skip if already processed
        if analyte_name_lower in processed_analyte_names:
            continue
        if not is_valid_analyte_name(analyte_name):
            continue
        
        # Check that ratio parts are not common units
        ratio_parts = ratio_name.split('/')
        if any(part.lower() in ['ml', 'dl', 'l', 'dl', 'mg', 'g', 'ng', 'pg', 'mcg', 'iu', 'u'] 
               for part in ratio_parts):
            continue
        
        processed_analyte_names.add(analyte_name_lower)
        
        value_str = match.group(3).replace(',', '.')
        try:
            value = float(value_str)
        except ValueError:
            continue
        
        ref_range = None
        if match.group(4):
            ref_range = match.group(4).strip()
            # Normalize ref range: handle different separators
            ref_range = re.sub(r'\s+', ' ', ref_range)
        
        items.append(ImportedLabItem(
            analyte_name=analyte_name,
            value=value,
            unit=None,  # Ratios don't have units
            material=None,
            taken_at=None,
            ref_range=ref_range
        ))
    
    # Pattern for standard test with value, unit, and ref range
    # Example: "Glucosa 94.2 mg/dL 70 a 100" or "ANTIGENO PROSTATICO ESPECIFICO 0.65 ng/mL 0.0 a 2.5"
    # More strict: analyte name must be at least 4 characters, unit must be valid
    pattern_standard = re.compile(
        r'\b([A-ZÁÉÍÓÚÑÜÇ][A-ZÁÉÍÓÚÑÜÇa-záéíóúñüç\s]{3,}?)\s*[:]?\s*'  # Analyte name (min 4 chars, may have colon)
        r'([\d,\.]+)\s+'  # Value (can have comma or dot)
        r'((?=.*[A-Za-zµ])[A-Za-zµ/%²³\d\.\-]{2,})\s+'  # Unit must contain a letter and be at least 2 chars
        r'([\d,\.]+\s*(?:a|a|–|-|to|до)\s*[\d,\.]+)',  # Ref range (required: "10 a 20", "0.0-2.5")
        re.IGNORECASE
    )
    
    # Second pass: handle standard tests with ref range
    for match in pattern_standard.finditer(text):
        analyte_name = match.group(1).strip()
        analyte_name = re.sub(r'\s+', ' ', analyte_name).strip()
        
        # Skip if name is too short or invalid
        if len(analyte_name) < 4:
            continue
        
        analyte_name_lower = analyte_name.lower()
        
        # Skip if already processed or invalid
        if analyte_name_lower in processed_analyte_names:
            continue
        if not is_valid_analyte_name(analyte_name):
            continue
        # Skip if it looks like a ratio but wasn't caught by ratio pattern
        if '/' in analyte_name and any(part.strip().isupper() and len(part.strip()) <= 4 
                                       for part in analyte_name.split('/')):
            continue
        
        processed_analyte_names.add(analyte_name_lower)
        
        value_str = match.group(2).replace(',', '.')
        try:
            value = float(value_str)
        except ValueError:
            continue
        
        unit = match.group(3).strip() if match.group(3) else None
        # Validate unit - should not be empty and should look like a unit
        if unit and (len(unit) < 2 or len(unit) > 15):
            continue
        
        ref_range = match.group(4).strip() if match.group(4) else None
        
        if ref_range:
            ref_range = re.sub(r'\s+', ' ', ref_range)
        
        items.append(ImportedLabItem(
            analyte_name=analyte_name,
            value=value,
            unit=unit,
            material=None,
            taken_at=None,
            ref_range=ref_range
        ))
    
    # Pattern for test without ref range
    # Example: "Colesterol No Hdl 160 mg/dL"
    # More conservative: only match if we have good confidence it's a test result
    pattern_no_ref = re.compile(
        r'\b([A-ZÁÉÍÓÚÑÜÇ][A-ZÁÉÍÓÚÑÜÇa-záéíóúñüç\s]{4,}?)\s*[:]?\s*'  # Analyte name (min 5 chars)
        r'([\d,\.]+)\s+'  # Value
        r'((?=.*[A-Za-zµ])[A-Za-zµ/%²³\d\.\-]{2,})(?:\s|$)',  # Unit must contain letter
        re.IGNORECASE
    )
    
    # Third pass: handle tests without ref range (more conservative)
    for match in pattern_no_ref.finditer(text):
        analyte_name = match.group(1).strip()
        analyte_name = re.sub(r'\s+', ' ', analyte_name).strip()
        
        # Skip if name is too short
        if len(analyte_name) < 5:  # More strict for tests without ref range
            continue
        
        analyte_name_lower = analyte_name.lower()
        
        # Skip if already processed or invalid
        if analyte_name_lower in processed_analyte_names:
            continue
        if not is_valid_analyte_name(analyte_name):
            continue
        # Skip if it looks like a ratio
        if '/' in analyte_name and any(part.strip().isupper() and len(part.strip()) <= 4 
                                       for part in analyte_name.split('/')):
            continue
        
        processed_analyte_names.add(analyte_name_lower)
        
        value_str = match.group(2).replace(',', '.')
        try:
            value = float(value_str)
        except ValueError:
            continue
        
        unit = match.group(3).strip() if match.group(3) else None
        # Validate unit
        if unit and (len(unit) < 2 or len(unit) > 15):
            continue
        
        items.append(ImportedLabItem(
            analyte_name=analyte_name,
            value=value,
            unit=unit,
            material=None,
            taken_at=None,
            ref_range=None
        ))
    
    # Post-processing: remove duplicates and fragments
    # If we have items with similar names and same value/unit, keep the longest name
    final_items = []
    
    # Sort items by name length (longest first) to prefer full names over fragments
    items_sorted = sorted(items, key=lambda x: len(x.analyte_name), reverse=True)
    
    for item in items_sorted:
        # Skip if name is too short or invalid
        if not is_valid_analyte_name(item.analyte_name) or len(item.analyte_name) < 4:
            continue
        
        # Check if this item is a duplicate or fragment of an existing item
        is_duplicate = False
        item_lower = item.analyte_name.lower()
        
        for existing_item in final_items:
            existing_lower = existing_item.analyte_name.lower()
            
            # Check if same value and unit (or similar)
            same_data = (
                existing_item.value == item.value and
                existing_item.unit == item.unit
            )
            
            if same_data:
                # Check if one name is a substring of the other
                if item_lower in existing_lower:
                    # Current item is a fragment of existing, skip it
                    is_duplicate = True
                    break
                elif existing_lower in item_lower:
                    # Existing is a fragment of current, replace it
                    final_items.remove(existing_item)
                    break
                # Check for very similar names (one word difference)
                existing_words = set(existing_lower.split())
                item_words = set(item_lower.split())
                # If one set is almost a subset of the other, they're likely duplicates
                if existing_words and item_words:
                    overlap = len(existing_words & item_words)
                    min_words = min(len(existing_words), len(item_words))
                    if overlap >= min_words * 0.8 and min_words > 1:
                        # Very similar names, keep the longer one
                        if len(item.analyte_name) > len(existing_item.analyte_name):
                            final_items.remove(existing_item)
                            break
                        else:
                            is_duplicate = True
                            break
        
        if not is_duplicate:
            final_items.append(item)

    # Additional cleanup: drop items with clearly invalid units
    valid_units_short = {'ph'}
    cleaned_items = []
    for item in final_items:
        if item.unit:
            unit_lower = item.unit.lower()
            if unit_lower in {'a', '-'}:
                continue
            if len(unit_lower) == 1 and unit_lower not in valid_units_short:
                continue
            if unit_lower in {'hrs', 'hr', 'h'}:
                continue
        cleaned_items.append(item)

    # Apply known name corrections for truncated headings
    name_corrections = {
        'de filtracion glomerular': 'TASA DE FILTRACION GLOMERULAR',
        'no hdl': 'COLESTEROL NO HDL'
    }

    for item in cleaned_items:
        key = item.analyte_name.lower()
        if key in name_corrections:
            item.analyte_name = name_corrections[key]

    final_items = cleaned_items
 
    return final_items


def parse_pdf_to_import_json(pdf_bytes: bytes, patient_id: Union[str, int], source_pdf: Optional[str] = None) -> ImportJson:
    """
    Parse PDF and return ImportJson using refactored pipeline.
    
    Pipeline:
    1. Extract rows with coordinates from PDF (RawRow)
    2. Map rows to structured analytes (RawAnalyte)
    3. Normalize to final JSON structure (ImportedLabItem)
    
    Args:
        pdf_bytes: PDF file content as bytes
        patient_id: Patient identifier
        source_pdf: Optional source PDF filename
        
    Returns:
        ImportJson object with parsed results
        
    Raises:
        ValueError: If PDF is empty or invalid
        NoTextLayerError: If no text layer is found
    """
    def _looks_like_bad_items(items):
        """
        Очень грубая проверка качества результата.
        
        Если ВСЕ элементы имеют "name" вида числа (типа "0.65") и нет ни одного
        нормального названия аналита, считаем, что новый пайплайн промахнулся,
        и лучше использовать старый regex-парсер.
        """
        if not items:
            return True
        
        has_normal_name = False
        for it in items:
            name = getattr(it, "analyte_name", "") or ""
            name = str(name).strip()
            # Чисто числовое (0.65, 123, 1,23)
            if re.fullmatch(r"[<>~=]?\s*\d+(?:[.,]\d+)?", name):
                continue
            # Слишком короткое имя
            if len(name) < 2:
                continue
            has_normal_name = True
            break
        
        return not has_normal_name

    try:
        # Step 1: Extract structured rows with coordinates
        rows = extract_rows_from_pdf(pdf_bytes)
        
        # Step 1.5: Extract date from PDF header
        extracted_date = extract_date_from_pdf(rows)
        if extracted_date:
            print(f"Extracted date from PDF: {extracted_date.strftime('%Y-%m-%d')}")
        else:
            print("Warning: Could not extract date from PDF")
        
        # Step 2: Try LLM-based normalization if enabled
        items = None
        normalization_method = "rule-based"
        
        if is_llm_enabled():
            try:
                print("Attempting LLM-based normalization...")
                items = normalize_with_llm(rows, extracted_date=extracted_date)
                if items:
                    normalization_method = "llm"
            except Exception as e:
                print(f"LLM normalization failed: {e}")
                print("Falling back to rule-based normalization")
                items = None
        
        # Step 3: Fall back to rule-based normalization if needed
        if items is None:
            print("Using rule-based normalization...")
            raw_analytes = build_raw_analytes(rows)
            items = normalize_analytes(raw_analytes, extracted_date=extracted_date)
            normalization_method = "rule-based"
        # Simple quality check: если все имена выглядят как числа, то это не то
        if _looks_like_bad_items(items):
            print(
                "Warning: normalized items look invalid (all names are numeric). "
                "Falling back to simple regex parser."
            )
            text = extract_text_from_pdf(pdf_bytes)
            legacy_items = basic_regex_extract_to_items(
                text, extracted_date=extracted_date
            )
            return ImportJson(
                patient_id=patient_id,
                items=legacy_items,
                source_pdf=source_pdf,
                normalization_method="rule-based-basic-regex-fallback",
            )
        
        return ImportJson(
            patient_id=patient_id,
            items=items,
            source_pdf=source_pdf,
            normalization_method=normalization_method
        )
    except ExtractorNoTextLayerError as e:
        raise NoTextLayerError(str(e))
    except Exception as e:
        # Log error and fall back to old method if needed
        print(f"Warning: New pipeline failed ({e}), falling back to legacy parser")
        try:
            text = extract_text_from_pdf(pdf_bytes)
            items = parse_lab_results(text)
            return ImportJson(
                patient_id=patient_id,
                items=items,
                source_pdf=source_pdf,
                normalization_method="rule-based-legacy"
            )
        except Exception as fallback_error:
            raise ValueError(f"Both parsers failed: {e}, {fallback_error}")

