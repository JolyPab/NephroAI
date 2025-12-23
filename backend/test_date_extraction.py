"""Simple script to test date extraction from PDF."""

import sys
from pathlib import Path
from pdf_parser import parse_pdf_to_import_json, extract_rows_from_pdf
from pdf_parser import extract_date_from_pdf

def test_date_extraction(pdf_path: str):
    """Test date extraction from a PDF file."""
    print(f"Testing date extraction from: {pdf_path}")
    print("-" * 60)
    
    # Read PDF file
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"ERROR: File not found: {pdf_path}")
        return
    
    with open(pdf_file, 'rb') as f:
        pdf_bytes = f.read()
    
    print(f"PDF size: {len(pdf_bytes)} bytes")
    
    # Extract rows
    try:
        rows = extract_rows_from_pdf(pdf_bytes)
        print(f"Extracted {len(rows)} rows from PDF")
    except Exception as e:
        print(f"ERROR: Failed to extract rows: {e}")
        return
    
    # Extract date
    print("\n--- Extracting date from PDF header ---")
    extracted_date = extract_date_from_pdf(rows)
    
    if extracted_date:
        print(f"✅ SUCCESS: Date extracted: {extracted_date.strftime('%Y-%m-%d')}")
        print(f"   Full datetime: {extracted_date}")
    else:
        print("❌ WARNING: Could not extract date from PDF")
        print("\nFirst 20 rows (for debugging):")
        for i, row in enumerate(rows[:20]):
            row_text = " | ".join(cell.text[:50] for cell in row.cells[:5])
            print(f"  Row {i}: {row_text}")
    
    # Test full parsing
    print("\n--- Testing full parsing ---")
    try:
        result = parse_pdf_to_import_json(pdf_bytes, patient_id="test", source_pdf=pdf_file.name)
        
        print(f"Total items parsed: {len(result.items)}")
        
        # Check if items have dates
        items_with_date = [item for item in result.items if item.taken_at]
        items_without_date = [item for item in result.items if not item.taken_at]
        
        print(f"Items with date: {len(items_with_date)}")
        print(f"Items without date: {len(items_without_date)}")
        
        if items_with_date:
            print(f"\n✅ First item with date:")
            item = items_with_date[0]
            print(f"   Analyte: {item.analyte_name}")
            print(f"   Date: {item.taken_at.strftime('%Y-%m-%d')}")
            print(f"   Value: {item.value} {item.unit}")
        
        if items_without_date and extracted_date:
            print(f"\n⚠️  WARNING: Date was extracted but not applied to items!")
            print(f"   This might indicate a bug in the normalizer.")
        
    except Exception as e:
        print(f"ERROR: Failed to parse PDF: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_date_extraction.py <path_to_pdf>")
        print("\nExample:")
        print("  python test_date_extraction.py ../media/013231840002.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    test_date_extraction(pdf_path)



