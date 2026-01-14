"""Test script for new parser."""

import sys
import json
sys.path.append('.')

from pdf_parser import parse_pdf_to_import_json

# Test with real PDF
result = parse_pdf_to_import_json(
    open('013241970006.pdf', 'rb').read(),
    '123',
    '013241970006.pdf'
)

with open('test_results.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total items: {len(result.items)}\n\n")
    
    # Show specific tests
    test_analytes = ['GLUCOSA', 'UREA', 'CREATININA', 'BUN', 'DENSIDAD']
    
    for test_name in test_analytes:
        item = next((i for i in result.items if test_name in i.analyte_name), None)
        if item:
            f.write(f"{test_name}:\n")
            f.write(f"  Name: {item.analyte_name}\n")
            f.write(f"  Value: {item.value}\n")
            f.write(f"  Value Text: {item.value_text}\n")
            f.write(f"  Unit: {item.unit}\n")
            f.write(f"  Ref Range: {item.ref_range}\n")
            f.write('\n')
        else:
            f.write(f"{test_name}: NOT FOUND\n\n")

print("Results written to test_results.txt")

