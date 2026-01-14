"""Normalize raw analytes into final JSON structure."""

import re
from typing import List, Optional
from datetime import datetime
from backend.pdf_structures import RawAnalyte
from backend.models import ImportedLabItem


def normalize_analytes(raw_analytes: List[RawAnalyte], extracted_date: Optional[datetime] = None) -> List[ImportedLabItem]:
    """
    Convert RawAnalyte objects to ImportedLabItem with normalization.
    
    Normalization rules:
    - analyte_name: uppercase, trimmed, collapsed spaces
    - value: parse as float if possible, otherwise keep as text in value_text
    - unit: clean and validate
    - ref_range: clean, keep multi-line descriptions
    - taken_at: use extracted date if provided
    
    Args:
        raw_analytes: List of RawAnalyte objects to normalize
        extracted_date: Optional datetime extracted from PDF header
    """
    items = []
    
    for raw in raw_analytes:
        item = normalize_single_analyte(raw, extracted_date)
        if item:
            items.append(item)
    
    # Validate and log warnings
    _validate_items(items, raw_analytes)
    
    return items


def split_concatenated_words(name: str) -> str:
    """
    Basic word splitting for rule-based fallback.
    
    When LLM is used, it handles word splitting better.
    This is just a simple fallback for common cases.
    """
    if not name or len(name) < 10:
        return name
    
    # Only most common patterns for fallback
    patterns = [
        # Electrolytes
        (r'(SODIO|POTASIO|CLORO|FOSFORO|CALCIO|MAGNESIO)(SERICO)', r'\1 \2'),
        # DE patterns
        (r'([A-Z]{5,})(DE)([A-Z]{4,})', r'\1 \2 \3'),
        # Common suffixes
        (r'(COLESTEROL|BILIRRUBINA)(TOTAL)', r'\1 \2'),
    ]
    
    result = name
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    
    return result


def normalize_single_analyte(raw: RawAnalyte, extracted_date: Optional[datetime] = None) -> Optional[ImportedLabItem]:
    """
    Normalize a single RawAnalyte.
    """
    def _parse_numeric(value_str: str) -> Optional[float]:
        """
        Parse numeric values handling decimal commas and thousand separators.
        """
        if not value_str:
            return None

        v = value_str.strip().replace(" ", "")

        # Pattern: 1,234.56 (comma thousands, dot decimal)
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", v):
            try:
                return float(v.replace(",", ""))
            except ValueError:
                return None

        # Pattern: 1.234,56 (dot thousands, comma decimal) - require comma to avoid misreading 1.008 as 1008
        if "," in v and re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", v):
            try:
                return float(v.replace(".", "").replace(",", "."))
            except ValueError:
                return None

        # Pattern: 74,8 (comma decimal only)
        if "," in v and "." not in v:
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None

        # Fallback: parse as-is
        try:
            return float(v)
        except ValueError:
            return None

    NAME_CORRECTIONS = {
        "COLESTEROLDEALTA DE NSIDAD": "COLESTEROL DE ALTA DENSIDAD",
        "COLESTEROLDEBAJA DE NSIDAD": "COLESTEROL DE BAJA DENSIDAD",
    }

    # Normalize analyte name
    analyte_name = raw.analyte_raw.strip()
    analyte_name = analyte_name.upper()
    
    # Split concatenated words BEFORE collapsing spaces
    analyte_name = split_concatenated_words(analyte_name)
    
    # Collapse multiple spaces into one
    analyte_name = re.sub(r'\s+', ' ', analyte_name)

    # Apply explicit corrections for known glitches
    if analyte_name in NAME_CORRECTIONS:
        analyte_name = NAME_CORRECTIONS[analyte_name]
    
    if not analyte_name or len(analyte_name) < 2:
        return None
    
    # Normalize value
    value = None
    value_text = None
    
    if raw.value_raw:
        value_str = raw.value_raw.strip()
        
        parsed_value = _parse_numeric(value_str)
        if parsed_value is not None:
            value = parsed_value
        else:
            # Not a number, keep as text
            value_text = value_str
    
    # Normalize unit
    unit = None
    if raw.unit_raw:
        unit_str = raw.unit_raw.strip()
        
        # Unit should not be purely numeric
        if not re.match(r'^\d+\.?\d*$', unit_str):
            # Unit should contain letters or special chars
            if re.search(r'[a-zA-Z��/%�?�?]', unit_str):
                unit = unit_str
    
    # Normalize ref_range
    ref_range = None
    if raw.ref_range_raw:
        ref_str = raw.ref_range_raw.strip()
        
        # Skip if it's just a dash or empty
        if ref_str and ref_str not in ['-', '--', '�?"']:
            ref_range = ref_str

    # If value is textual (NEGATIVO, etc.) and ref_range just repeats it with stray chars, clean it
    if value_text and ref_range:
        ref_clean = ref_range.strip()
        if re.fullmatch(rf"{re.escape(value_text)}\s*a?", ref_clean, flags=re.IGNORECASE) or ref_clean.upper() == value_text.upper():
            ref_range = value_text
        else:
            ref_range = ref_clean
    
    return ImportedLabItem(
        analyte_name=analyte_name,
        value=value,
        value_text=value_text,
        unit=unit,
        material=None,  # Not extracting material yet
        taken_at=extracted_date,  # Use extracted date from PDF
        ref_range=ref_range
    )


def _validate_items(items: List[ImportedLabItem], raw_analytes: List[RawAnalyte]):
    """Validate and log warnings about parsed items."""
    # Check if we lost any items
    if len(items) != len(raw_analytes):
        print(f"Warning: {len(raw_analytes)} raw analytes -> {len(items)} final items. Some were dropped.")
    
    # Check for suspicious units
    for item in items:
        if item.unit:
            # Warn if unit looks like a number
            if re.match(r'^\d+\.?\d*$', item.unit):
                print(f"Warning: Suspicious numeric unit for {item.analyte_name}: {item.unit}")
            
            # Warn if unit looks like a range
            if re.search(r'\d+\s*a\s*\d+', item.unit):
                print(f"Warning: Unit looks like ref range for {item.analyte_name}: {item.unit}")
        
        # Check if value is out of ref range (if both are present and numeric)
        if item.value is not None and item.ref_range:
            _check_out_of_range(item)


def _check_out_of_range(item: ImportedLabItem):
    """Check if value is out of reference range."""
    if not item.ref_range:
        return
    
    # Try to extract min and max from ref_range
    # Pattern: "min a max" or "min - max" or "min to max"
    match = re.search(r'([\d.]+)\s*(?:a|-|to|�?")\s*([\d.]+)', item.ref_range)
    
    if match:
        try:
            ref_min = float(match.group(1))
            ref_max = float(match.group(2))
            
            if item.value < ref_min or item.value > ref_max:
                print(f"Info: {item.analyte_name} = {item.value} is out of range ({item.ref_range})")
        except (ValueError, AttributeError):
            pass
