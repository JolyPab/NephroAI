"""Test script for LLM-based normalization."""

import sys
import os

# Set environment variables for testing
os.environ["USE_LLM_NORMALIZATION"] = "true"
# os.environ["AITUNNEL_API_KEY"] = "sk-aitunnel-your-key"  # Uncomment and set your key
# os.environ["AITUNNEL_MODEL"] = "deepseek-r1"

sys.path.append('.')

from pdf_parser import parse_pdf_to_import_json

# Test with real PDF
try:
    result = parse_pdf_to_import_json(
        open('013241970006.pdf', 'rb').read(),
        '123',
        '013241970006.pdf'
    )
    
    with open('llm_test_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total items: {len(result.items)}\n\n")
        
        # Show first 10 analytes
        f.write("First 10 analytes:\n")
        f.write("=" * 80 + "\n\n")
        
        for item in result.items[:10]:
            f.write(f"Name: {item.analyte_name}\n")
            f.write(f"Value: {item.value}\n")
            f.write(f"Value Text: {item.value_text}\n")
            f.write(f"Unit: {item.unit}\n")
            f.write(f"Ref Range: {item.ref_range}\n")
            f.write('\n')
        
        # Test specific analytes
        f.write("\n" + "=" * 80 + "\n")
        f.write("Key test analytes:\n")
        f.write("=" * 80 + "\n\n")
        
        test_keywords = ['GLUCOSA', 'UREA', 'CREATININA', 'BUN', 'DENSIDAD']
        
        for keyword in test_keywords:
            item = next((i for i in result.items if keyword in i.analyte_name), None)
            if item:
                f.write(f"{keyword}:\n")
                f.write(f"  Name: {item.analyte_name}\n")
                f.write(f"  Value: {item.value}\n")
                f.write(f"  Unit: {item.unit}\n")
                f.write(f"  Ref Range: {item.ref_range}\n")
                f.write('\n')
            else:
                f.write(f"{keyword}: NOT FOUND\n\n")
    
    print("Results written to llm_test_results.txt")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

