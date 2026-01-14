"""Simple script to test API endpoints."""

import requests

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    """Test health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.status_code} - {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_preview(pdf_path: str, patient_id: str = "test_123"):
    """Test preview endpoint with a PDF file."""
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path, f, "application/pdf")}
        data = {"patient_id": patient_id}
        response = requests.post(f"{BASE_URL}/api/preview", files=files, data=data)
    
    print(f"Preview status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Parsed {len(result['items'])} items")
        for item in result["items"][:5]:  # Show first 5 items
            print(f"  - {item['analyte_name']}: {item['value']} {item['unit'] or ''}")
        return result
    else:
        print(f"Error: {response.text}")
        return None


def test_import(pdf_path: str, patient_id: str = "test_123"):
    """Test import endpoint with a PDF file."""
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path, f, "application/pdf")}
        data = {"patient_id": patient_id}
        response = requests.post(f"{BASE_URL}/api/import", files=files, data=data)
    
    print(f"Import status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Imported {result['items_count']} items")
        return result
    else:
        print(f"Error: {response.text}")
        return None


if __name__ == "__main__":
    import sys
    
    print("Testing Lab Import API\n")
    
    # Test health
    test_health()
    print()
    
    # Test with PDF if provided
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        patient_id = sys.argv[2] if len(sys.argv) > 2 else "test_123"
        
        print(f"Testing with PDF: {pdf_path}")
        print(f"Patient ID: {patient_id}\n")
        
        # Test preview
        print("=== Preview Test ===")
        test_preview(pdf_path, patient_id)
        print()
        
        # Test import
        print("=== Import Test ===")
        test_import(pdf_path, patient_id)
    else:
        print("Usage: python test_api.py <pdf_path> [patient_id]")
        print("Example: python test_api.py report.pdf 123")

