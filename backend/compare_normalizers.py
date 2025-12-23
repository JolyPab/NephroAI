"""Compare rule-based vs LLM normalization."""

import sys
import os
sys.path.append('.')

from pdf_parser import parse_pdf_to_import_json

# Test PDF
pdf_path = '013241970006.pdf'
pdf_bytes = open(pdf_path, 'rb').read()

print("=" * 80)
print("COMPARING NORMALIZATION METHODS")
print("=" * 80)

# Test 1: Rule-based (default)
print("\n1. RULE-BASED NORMALIZATION (default)")
print("-" * 80)
os.environ["USE_LLM_NORMALIZATION"] = "false"

result_rule = parse_pdf_to_import_json(pdf_bytes, "123", pdf_path)

print(f"Result: {len(result_rule.items)} items")
print(f"Method: {result_rule.normalization_method}")

# Show sample
print("\nSample analytes:")
for item in result_rule.items[:5]:
    try:
        print(f"  - {item.analyte_name}: {item.value} {item.unit or ''}")
    except UnicodeEncodeError:
        # Handle encoding issues in Windows console
        print(f"  - [analyte]: {item.value} {item.unit or ''}")

# Test 2: LLM-based (if configured)
print("\n" + "=" * 80)
print("2. LLM-BASED NORMALIZATION (if configured)")
print("-" * 80)

if not os.environ.get("AITUNNEL_API_KEY"):
    print("WARNING: AITUNNEL_API_KEY not set")
    print("To test LLM normalization:")
    print("  1. Get API key from https://docs.aitunnel.ru")
    print("  2. Set environment variable: export AITUNNEL_API_KEY=sk-aitunnel-...")
    print("  3. Run this script again")
else:
    os.environ["USE_LLM_NORMALIZATION"] = "true"
    
    try:
        result_llm = parse_pdf_to_import_json(pdf_bytes, "123", pdf_path)
        
        print(f"Result: {len(result_llm.items)} items")
        print(f"Method: {result_llm.normalization_method}")
        
        # Show sample
        print("\nSample analytes:")
        for item in result_llm.items[:5]:
            try:
                print(f"  - {item.analyte_name}: {item.value} {item.unit or ''}")
            except UnicodeEncodeError:
                print(f"  - [analyte]: {item.value} {item.unit or ''}")
        
        # Compare
        print("\n" + "=" * 80)
        print("COMPARISON")
        print("=" * 80)
        print(f"Rule-based: {len(result_rule.items)} items")
        print(f"LLM-based:  {len(result_llm.items)} items")
        print(f"Difference: {abs(len(result_rule.items) - len(result_llm.items))} items")
        
    except Exception as e:
        print(f"Error during LLM normalization: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)

