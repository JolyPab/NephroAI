"""Debug extraction process."""

import sys
sys.path.append('.')

from pdf_extractor import extract_rows_from_pdf, detect_column_positions

# Load PDF
pdf_bytes = open('013241970006.pdf', 'rb').read()

# Extract rows
rows = extract_rows_from_pdf(pdf_bytes)

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total rows extracted: {len(rows)}\n")
    f.write(f"Pages: {set(r.page for r in rows)}\n\n")
    
    # Show first few rows from page 0
    page_0_rows = [r for r in rows if r.page == 0][:30]
    
    f.write("First 30 rows from page 0:\n")
    f.write("=" * 80 + "\n")
    
    for i, row in enumerate(page_0_rows):
        f.write(f"\nRow {i} (y={row.y0:.1f}):\n")
        for j, cell in enumerate(row.cells):
            f.write(f"  Cell {j}: x={cell.x0:.1f}-{cell.x1:.1f}, text='{cell.text}'\n")
    
    # Detect columns
    f.write("\n" + "=" * 80 + "\n")
    f.write("Column positions for page 0:\n")
    col_pos = detect_column_positions(rows, page=0)
    for col_name, (x_min, x_max) in col_pos.items():
        f.write(f"  {col_name}: {x_min:.1f} - {x_max:.1f}\n")

print("Output written to debug_output.txt")

