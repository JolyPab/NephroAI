"""Map raw PDF rows to structured analyte objects."""

import re
from typing import List, Optional
from pdf_structures import RawRow, RawAnalyte, RawCell
from pdf_extractor import detect_column_positions


def is_header_row(row: RawRow) -> bool:
    """Check if row is a column header."""
    header_keywords = ['RESULTADOS', 'UNIDADES', 'VALORES', 'REFERENCIA', 'ANALITO', 'VALOR', 'INTERVALO', 'NOTA']
    
    text = ' '.join(cell.text.upper() for cell in row.cells)
    
    # If row contains multiple header keywords, it's likely a header
    matches = sum(1 for keyword in header_keywords if keyword in text)
    if matches >= 2:
        return True
    
    # Single-cell rows with only header keywords
    if len(row.cells) == 1 and any(keyword == row.cells[0].text.upper() for keyword in header_keywords):
        return True
    
    return False


def is_section_header(row: RawRow) -> bool:
    """Check if row is a section header (e.g., 'HEMATOLOGIA', 'BIOQUIMICA')."""
    # Section headers typically:
    # - Have 1-2 cells
    # - Are mostly uppercase
    # - Contain no numbers
    # - Are relatively short (< 50 chars)
    
    if len(row.cells) > 2:
        return False
    
    text = ' '.join(cell.text for cell in row.cells).strip()
    
    if len(text) > 50:
        return False
    
    # Must be mostly uppercase letters
    uppercase_letters = sum(1 for c in text if c.isupper())
    total_letters = sum(1 for c in text if c.isalpha())
    
    if total_letters == 0:
        return False
    
    if uppercase_letters / total_letters < 0.7:  # At least 70% uppercase
        return False
    
    # Must not contain numbers
    if re.search(r'\d', text):
        return False
    
    # Common section names
    section_keywords = ['HEMATOLOGIA', 'BIOQUIMICA', 'ORINA', 'UREA', 'CREATININA', 'LIPIDOS', 
                       'ELECTROLITOS', 'HEPATICO', 'RENAL', 'GLUCOSA', 'EVALUACION']
    
    text_upper = text.upper()
    if any(keyword in text_upper for keyword in section_keywords):
        return True
    
    return False


def is_continuation_row(row: RawRow, prev_analyte: Optional[RawAnalyte]) -> bool:
    """
    Check if row is a continuation of previous analyte's ref_range.
    
    These are rows like:
    - "Estadio 1, TFG Normal"
    - "Optimo"  
    - "Alto"
    - "< 15 a"
    """
    if not prev_analyte:
        return False
    
    # Must have few cells (1-3)
    if len(row.cells) > 3:
        return False
    
    text = ' '.join(cell.text for cell in row.cells).strip()
    
    # Must be short
    if len(text) > 80:
        return False
    
    # Check for continuation keywords
    continuation_keywords = [
        'ESTADIO', 'OPTIMO', 'ÓPTIMO', 'ALTO', 'BAJO', 'NORMAL', 'LIMÍTROFE', 'LÍMITE',
        'MODERADO', 'LEVE', 'SEVERO', 'DISMINUIDA', 'DISMINUIDO', 'AUMENTADO', 'AUMENTADA',
        'RIESGO', 'TFG', 'FALLO', 'RENAL', 'PROTEINURIA', 'MICROALBUMINURIA'
    ]
    
    text_upper = text.upper()
    if any(keyword in text_upper for keyword in continuation_keywords):
        return True
    
    # Check if it starts with a comparison operator or range fragment
    if re.match(r'^[<>≥≤]\s*\d+', text):
        return True
    
    if re.match(r'^\d+\s*a\s*\d*$', text):  # Fragment like "45 a 59" or "45 a"
        return True
    
    return False


def get_cell_in_column(row: RawRow, column_range: tuple) -> Optional[RawCell]:
    """Get the first cell that falls within the column x-range."""
    if not column_range:
        return None
    
    x_min, x_max = column_range
    
    for cell in row.cells:
        # Check if cell overlaps with column range
        if cell.x0 >= x_min and cell.x0 <= x_max:
            return cell
        # Also check if cell center is in range
        cell_center = (cell.x0 + cell.x1) / 2
        if x_min <= cell_center <= x_max:
            return cell
    
    return None


def get_cells_in_column(row: RawRow, column_range: tuple) -> List[RawCell]:
    """Get all cells that fall within the column x-range."""
    if not column_range:
        return []
    
    x_min, x_max = column_range
    cells = []
    
    for cell in row.cells:
        if cell.x0 >= x_min and cell.x0 <= x_max:
            cells.append(cell)
        else:
            cell_center = (cell.x0 + cell.x1) / 2
            if x_min <= cell_center <= x_max:
                cells.append(cell)
    
    return cells


def extract_numeric_value(text: str) -> Optional[str]:
    """Extract numeric value from text."""
    # Match patterns like: 123, 123.45, 123,45, +123, -123
    match = re.search(r'[+-]?\d+([.,]\d+)?', text)
    if match:
        return match.group(0)
    return None


def is_numeric(text: str) -> bool:
    """Check if text is purely numeric."""
    return bool(re.match(r'^[+-]?\d+([.,]\d+)?$', text.strip()))


def is_textual_value(text: str) -> bool:
    """Check if text is a textual lab value (NEGATIVO, POSITIVO, etc.)."""
    textual_values = ['NEGATIVO', 'NEG', 'POSITIVO', 'POS', 'TRAZA', 'TRAZAS', 
                     'AUSENTE', 'PRESENTE', 'NORMAL', 'ANORMAL']
    
    return text.upper().strip() in textual_values


def build_raw_analytes(rows: List[RawRow]) -> List[RawAnalyte]:
    """
    Convert raw rows to structured analyte objects.
    
    This function:
    - Detects column positions
    - Skips headers
    - Tracks section headers
    - Maps cells to analyte/value/unit/ref_range
    - Joins multi-line ref ranges
    """
    if not rows:
        return []
    
    # Check if this is a simple single-cell-per-row PDF (likely a test PDF)
    single_cell_rows = [row for row in rows if len(row.cells) == 1]
    if len(single_cell_rows) == len(rows):
        # Fall back to simple line-by-line parsing
        return build_raw_analytes_simple(rows)
    
    analytes = []
    current_section = None
    
    # Detect columns (do this per-page for better accuracy)
    pages = list(set(row.page for row in rows))
    column_positions_by_page = {}
    
    for page in pages:
        column_positions_by_page[page] = detect_column_positions(rows, page=page)
    
    row_index = 0
    skip_next = False
    
    while row_index < len(rows):
        row = rows[row_index]
        
        if skip_next:
            skip_next = False
            row_index += 1
            continue
        
        # Skip header rows
        if is_header_row(row):
            row_index += 1
            continue
        
        # Check for section header
        if is_section_header(row):
            section_text = ' '.join(cell.text for cell in row.cells).strip()
            current_section = section_text
            row_index += 1
            continue
        
        # Check if continuation of previous analyte
        if analytes and is_continuation_row(row, analytes[-1]):
            # Append to previous analyte's ref_range
            continuation_text = ' '.join(cell.text for cell in row.cells).strip()
            if analytes[-1].ref_range_raw:
                analytes[-1].ref_range_raw += '; ' + continuation_text
            else:
                analytes[-1].ref_range_raw = continuation_text
            row_index += 1
            continue
        
        # Try to map as regular data row
        column_pos = column_positions_by_page.get(row.page, {})
        
        analyte_cell = get_cell_in_column(row, column_pos.get('analyte'))
        value_cell = get_cell_in_column(row, column_pos.get('value'))
        unit_cell = get_cell_in_column(row, column_pos.get('unit'))
        ref_cells = get_cells_in_column(row, column_pos.get('ref_range'))
        
        # Must have at least analyte name to be valid
        if not analyte_cell or not analyte_cell.text.strip():
            row_index += 1
            continue
        
        analyte_raw = analyte_cell.text.strip()
        
        # Extract value
        value_raw = None
        if value_cell and value_cell.text.strip():
            value_text = value_cell.text.strip()
            # Check if it's textual value
            if is_textual_value(value_text):
                value_raw = value_text
            else:
                # Try to extract numeric value
                value_raw = extract_numeric_value(value_text)
                if not value_raw:
                    value_raw = value_text  # Keep as is
        
        # Extract unit
        unit_raw = None
        if unit_cell and unit_cell.text.strip():
            unit_text = unit_cell.text.strip()
            # Unit should not be purely numeric (that's likely part of ref range)
            if not is_numeric(unit_text):
                # Unit should contain letters or /
                if re.search(r'[a-zA-Zµ/]', unit_text):
                    unit_raw = unit_text
        
        # Extract ref range
        ref_range_raw = None
        if ref_cells:
            ref_texts = [cell.text.strip() for cell in ref_cells if cell.text.strip()]
            if ref_texts:
                ref_range_raw = ' '.join(ref_texts)

        # Skip rows that don't carry any value/unit/range data (likely headers/metadata)
        if value_raw is None and unit_raw is None and ref_range_raw is None:
            row_index += 1
            continue
        
        # Create analyte
        analyte = RawAnalyte(
            id=f"{row.page}-{row_index}",
            page=row.page,
            row_index=row_index,
            section=current_section,
            analyte_raw=analyte_raw,
            value_raw=value_raw,
            unit_raw=unit_raw,
            ref_range_raw=ref_range_raw,
            original_cells=row.cells
        )
        
        analytes.append(analyte)
        row_index += 1
    
    # Post-process: fix known bugs like DENSIDAD
    analytes = fix_densidad_bug(analytes, rows)
    
    return analytes


def fix_densidad_bug(analytes: List[RawAnalyte], rows: List[RawRow]) -> List[RawAnalyte]:
    """
    Fix the DENSIDAD bug where unit is incorrectly set to a number.
    
    For DENSIDAD:
    - value should be numeric (e.g., 1.008)
    - unit should be None (density has no unit)
    - ref_range should be like "1.005 a 1.035"
    
    The bug occurs when the ref_range is parsed as unit.
    """
    for i, analyte in enumerate(analytes):
        if 'DENSIDAD' not in analyte.analyte_raw.upper():
            continue
        
        # Check if we have the suspicious pattern:
        # - value is numeric
        # - unit is also numeric
        # - ref_range is empty or "-"
        
        if not analyte.value_raw:
            continue
        
        if not is_numeric(analyte.value_raw):
            continue
        
        if not analyte.unit_raw or not is_numeric(analyte.unit_raw):
            continue
        
        if analyte.ref_range_raw and analyte.ref_range_raw.strip() not in ['', '-']:
            continue
        
        # This looks like the bug! The unit is actually part of the ref range.
        # Look for ref range in the same row or next row
        
        # First, check if unit + following cells form a range
        # e.g., unit="1.005", and there's another cell with "a 1.035"
        
        # Look at original cells
        if analyte.original_cells:
            # Find cells after the unit cell
            unit_cell_idx = None
            for idx, cell in enumerate(analyte.original_cells):
                if cell.text.strip() == analyte.unit_raw:
                    unit_cell_idx = idx
                    break
            
            if unit_cell_idx is not None and unit_cell_idx < len(analyte.original_cells) - 1:
                # Check following cells
                remaining_cells = analyte.original_cells[unit_cell_idx + 1:]
                remaining_text = ' '.join(cell.text.strip() for cell in remaining_cells)
                
                # Try to build ref range
                potential_range = analyte.unit_raw + ' ' + remaining_text
                
                # Check if it looks like a range
                if re.search(r'\d+\.?\d*\s*a\s*\d+\.?\d*', potential_range):
                    # Fix it!
                    analyte.ref_range_raw = potential_range.strip()
                    analyte.unit_raw = None
                    continue
        
        # If that didn't work, try looking at the next row
        if i + 1 < len(analytes):
            next_analyte = analytes[i + 1]
            
            # Check if next row looks like a continuation with just a range
            if next_analyte.original_cells and len(next_analyte.original_cells) <= 2:
                next_text = ' '.join(cell.text for cell in next_analyte.original_cells).strip()
                
                # Build potential range
                potential_range = analyte.unit_raw + ' ' + next_text
                
                if re.search(r'\d+\.?\d*\s*a\s*\d+\.?\d*', potential_range):
                    # Fix it!
                    analyte.ref_range_raw = potential_range.strip()
                    analyte.unit_raw = None
                    # Mark next analyte for removal (it's not a real analyte)
                    next_analyte.analyte_raw = '__REMOVE__'
    
    # Remove marked analytes
    analytes = [a for a in analytes if a.analyte_raw != '__REMOVE__']
    
    return analytes


def build_raw_analytes_simple(rows: List[RawRow]) -> List[RawAnalyte]:
    """
    Simple fallback for single-cell rows (e.g. test PDFs).
    
    Parses lines like:
      "Glucosa 94.2 mg/dL 70 a 100"
      "RELACION BUN/CRE 14.75 10 a 20"
    """
    raw_analytes = []
    analyte_counter = 0
    
    for row_idx, row in enumerate(rows):
        if not row.cells:
            continue
        
        text = row.cells[0].text.strip()
        
        # Skip empty lines
        if not text or len(text) < 3:
            continue
        
        # Skip common headers/footers
        if any(skip in text.upper() for skip in ['PAGINA', 'PACIENTE', 'SERVICIO', 'FECHA', 'METODO']):
            continue
        
        # Try to parse: "NAME VALUE UNIT RANGE"
        # Pattern: text + number + optional unit + optional range
        
        # Look for a number in the line
        number_match = re.search(r'(\d+[.,]\d+|\d+)', text)
        if not number_match:
            continue
        
        value_str = number_match.group(1)
        value_pos = number_match.start()
        
        # Everything before the number is the analyte name
        analyte_name = text[:value_pos].strip()
        if not analyte_name or len(analyte_name) < 2:
            continue
        
        # Everything after the number is unit + ref_range
        rest = text[number_match.end():].strip()
        
        # Try to split unit and ref_range
        unit = None
        ref_range = None
        
        if rest:
            # Look for common units
            unit_match = re.match(r'^([a-zA-Z/%²³\d\.\-]+)', rest)
            if unit_match:
                unit = unit_match.group(1)
                # Rest after unit is ref_range
                ref_range_start = unit_match.end()
                ref_range = rest[ref_range_start:].strip()
                if ref_range and not any(c.isdigit() for c in ref_range):
                    # If ref_range has no digits, it's probably not a range
                    ref_range = None
            else:
                # No clear unit, maybe just ref_range
                if any(c.isdigit() for c in rest):
                    ref_range = rest
        
        # Create raw analyte
        analyte_counter += 1
        raw_analytes.append(RawAnalyte(
            id=f"simple_{analyte_counter}",
            page=row.page,
            row_index=row_idx,
            section=None,
            analyte_raw=analyte_name,
            value_raw=value_str,
            unit_raw=unit,
            ref_range_raw=ref_range
        ))
    
    return raw_analytes
