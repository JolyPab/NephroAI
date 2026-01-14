"""List all parsed analytes."""

import sys
sys.path.append('.')

from pdf_parser import parse_pdf_to_import_json

# Test with real PDF
result = parse_pdf_to_import_json(
    open('013241970006.pdf', 'rb').read(),
    '123',
    '013241970006.pdf'
)

# Find relevant analytes
with open('all_analytes.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total items: {len(result.items)}\n\n")
    
    # Find ones containing keywords
    keywords = ['BUN', 'CREATININA', 'DENSIDAD', 'UREA']
    
    for keyword in keywords:
        f.write(f"\n{'='*80}\n")
        f.write(f"Analytes containing '{keyword}':\n")
        f.write('='*80 + '\n\n')
        
        matches = [i for i in result.items if keyword in i.analyte_name]
        for item in matches:
            f.write(f"Name: {item.analyte_name}\n")
            f.write(f"Value: {item.value}\n")
            f.write(f"Unit: {item.unit}\n")
            f.write(f"Ref Range: {item.ref_range}\n")
            f.write('\n')

print("Results written to all_analytes.txt")

