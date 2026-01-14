"""PDF extraction with coordinates using pdfplumber."""

import io
import re
from typing import List, Optional
import pdfplumber
from collections import defaultdict

from backend.pdf_structures import RawCell, RawRow


class NoTextLayerError(Exception):
    """Raised when PDF has no text layer."""
    pass


def extract_rows_from_pdf(pdf_bytes: bytes) -> List[RawRow]:
    """
    Extract structured rows from PDF with coordinates.
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        List of RawRow objects with cells and coordinates
        
    Raises:
        ValueError: If PDF is empty or invalid
        NoTextLayerError: If no text layer is found in PDF
    """
    if not pdf_bytes or len(pdf_bytes) < 100:
        raise ValueError("Empty or invalid PDF file")
    
    all_rows = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract words with coordinates
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=True,
                )
                
                if not words:
                    continue
                
                # Group words into rows based on y-coordinate proximity
                rows_dict = defaultdict(list)
                for word in words:
                    # Use top coordinate for grouping, with tolerance
                    y_key = round(word['top'] / 2) * 2  # Group by ~2pt intervals
                    rows_dict[y_key].append(word)
                
                # Convert to RawRow objects
                for y_key in sorted(rows_dict.keys()):
                    words_in_row = sorted(rows_dict[y_key], key=lambda w: w['x0'])
                    
                    if not words_in_row:
                        continue
                    
                    # Calculate row bounds
                    row_y0 = min(w['top'] for w in words_in_row)
                    row_y1 = max(w['bottom'] for w in words_in_row)
                    
                    # Group words into cells based on x-proximity
                    cells = []
                    current_cell_words = []
                    last_x1 = None
                    
                    for word in words_in_row:
                        # If words are close together (< 10pt gap), group them into same cell
                        if last_x1 is None or word['x0'] - last_x1 < 10:
                            current_cell_words.append(word)
                            last_x1 = word['x1']
                        else:
                            # Start new cell
                            if current_cell_words:
                                cells.append(_create_cell_from_words(current_cell_words, page_num))
                            current_cell_words = [word]
                            last_x1 = word['x1']
                    
                    # Add last cell
                    if current_cell_words:
                        cells.append(_create_cell_from_words(current_cell_words, page_num))
                    
                    if cells:
                        all_rows.append(RawRow(
                            page=page_num,
                            cells=cells,
                            y0=row_y0,
                            y1=row_y1
                        ))
            
            if not all_rows:
                raise NoTextLayerError("No text layer found in PDF. PDF appears to be image-based.")
            
            return all_rows
            
    except pdfplumber.exceptions.PDFSyntaxError as e:
        raise ValueError(f"Invalid PDF: {e}")
    except Exception as e:
        if "No text layer" in str(e):
            raise
        raise NoTextLayerError(f"Failed to extract text from PDF: {e}")


def _create_cell_from_words(words: List[dict], page: int) -> RawCell:
    """Create a RawCell from a list of words."""
    x0 = min(w['x0'] for w in words)
    x1 = max(w['x1'] for w in words)
    y0 = min(w['top'] for w in words)
    y1 = max(w['bottom'] for w in words)
    
    # Join text with spaces, collapse multiple spaces
    text = ' '.join(w['text'] for w in words)
    text = ' '.join(text.split())  # Collapse whitespace
    
    return RawCell(
        page=page,
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        text=text
    )


def detect_column_positions(rows: List[RawRow], page: Optional[int] = None) -> dict:
    """
    Detect column positions based on x-coordinates of cells.
    
    Args:
        rows: List of RawRow objects
        page: Optional page number to filter rows (None = all pages)
        
    Returns:
        Dictionary with column ranges: {
            'analyte': (x_min, x_max),
            'value': (x_min, x_max),
            'unit': (x_min, x_max),
            'ref_range': (x_min, x_max)
        }
    """
    if page is not None:
        rows = [r for r in rows if r.page == page]
    
    if not rows:
        return {}
    
    # Collect rows that look like real data rows (avoid headers/metadata)
    candidate_rows = []
    for row in rows:
        # Only consider rows with a table-like shape
        if len(row.cells) < 3 or len(row.cells) > 5:
            continue
        
        # Must contain at least one number (likely value or range)
        if not any(re.search(r'\d+\.?\d*', cell.text) for cell in row.cells):
            continue
        
        # Skip obvious metadata/header rows
        first_text = row.cells[0].text.upper()
        metadata_keywords = ['NUMERO', 'PACIENTE', 'FECHA', 'IMP.', 'PAG.', 'REGISTRO', 'LIBERACION', 'REFERENCIA']
        if any(keyword in first_text for keyword in metadata_keywords):
            continue
        if ':' in first_text:  # rows like "IMP. DE RESULTADOS:" or similar
            continue
        
        candidate_rows.append(row)

    # If everything was filtered out, fall back to the original set so we don't return empty ranges
    if not candidate_rows:
        candidate_rows = [
            row for row in rows
            if len(row.cells) >= 3 and len(row.cells) <= 5
            and any(re.search(r'\d+\.?\d*', cell.text) for cell in row.cells)
        ]

    # Keep rows whose leftmost cell is close to the left margin (real data rows are usually left aligned)
    if candidate_rows:
        min_x = min(min(cell.x0 for cell in row.cells) for row in candidate_rows)
        # If everything is centered far to the right, it's probably metadata rather than data rows
        if min_x > 220:
            return {}
        x_threshold = min_x + 80  # allow some indentation but drop center-aligned headers
        candidate_rows = [
            row for row in candidate_rows
            if min(cell.x0 for cell in row.cells) <= x_threshold
        ] or candidate_rows

    x_positions_by_column = {0: [], 1: [], 2: [], 3: []}
    
    # Collect x0 positions from candidate rows
    for row in candidate_rows:
        for i, cell in enumerate(row.cells[:4]):  # Max 4 columns
            x_positions_by_column[i].append(cell.x0)
    
    # Calculate median position for each column
    column_x_ranges = {}
    
    if x_positions_by_column[0]:
        # Analyte column (leftmost)
        analyte_xs = sorted(x_positions_by_column[0])
        analyte_x = analyte_xs[len(analyte_xs) // 2]  # Median
        column_x_ranges['analyte'] = (analyte_x - 40, analyte_x + 150)
    
    if x_positions_by_column[1]:
        # Value column
        value_xs = sorted(x_positions_by_column[1])
        value_x = value_xs[len(value_xs) // 2]  # Median
        column_x_ranges['value'] = (value_x - 20, value_x + 40)
    
    if x_positions_by_column[2]:
        # Unit column
        unit_xs = sorted(x_positions_by_column[2])
        unit_x = unit_xs[len(unit_xs) // 2]  # Median
        column_x_ranges['unit'] = (unit_x - 20, unit_x + 40)
    
    if x_positions_by_column[3]:
        # Ref range column(s)
        ref_xs = sorted(x_positions_by_column[3])
        ref_x = ref_xs[len(ref_xs) // 2]  # Median
        column_x_ranges['ref_range'] = (ref_x - 20, 1000)  # Open-ended to right
    
    return column_x_ranges
