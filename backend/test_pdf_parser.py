"""Unit tests for PDF parser."""

import pytest
import fitz  # PyMuPDF
import io
from models import ImportedLabItem, ImportJson
from pdf_parser import (
    extract_text_from_pdf,
    parse_lab_results,
    parse_pdf_to_import_json,
    NoTextLayerError,
)
from database import (
    create_db_engine,
    get_session_factory,
    init_db,
    save_import_to_db,
    LabResult,
)


def create_test_pdf_with_text(text: str) -> bytes:
    """Create a test PDF with given text."""
    doc = fitz.open()  # Create new PDF
    page = doc.new_page()
    page.insert_text((72, 72), text)  # Insert text at position
    pdf_bytes = doc.tobytes()  # Convert to bytes
    doc.close()
    return pdf_bytes


def test_basic_parsing():
    """Test basic parsing of lab results."""
    test_text = """Glucosa 5.4 mmol/L 3.9 a 5.8
Urea 7.8 mmol/L 2.5 a 7.1"""
    
    pdf_bytes = create_test_pdf_with_text(test_text)
    text = extract_text_from_pdf(pdf_bytes)
    items = parse_lab_results(text)
    
    assert len(items) >= 1
    
    glucosa = next((item for item in items if "Glucosa" in item.analyte_name), None)
    assert glucosa is not None
    assert abs(glucosa.value - 5.4) < 0.01
    assert glucosa.unit == "mmol/L"
    assert glucosa.ref_range == "3.9 a 5.8"


def test_bun_cre_parsing():
    """Test parsing of BUN/CRE ratio."""
    test_text = """RELACION BUN/CRE
Relacion BUN/CRE 14.75 10 a 20"""
    
    pdf_bytes = create_test_pdf_with_text(test_text)
    text = extract_text_from_pdf(pdf_bytes)
    items = parse_lab_results(text)
    
    # Find BUN/CRE item
    bun_cre = next((item for item in items if "BUN/CRE" in item.analyte_name.upper()), None)
    assert bun_cre is not None, f"No BUN/CRE found in items: {[i.analyte_name for i in items]}"
    assert abs(bun_cre.value - 14.75) < 0.01
    assert bun_cre.unit is None
    assert bun_cre.ref_range == "10 a 20"


def test_empty_pdf():
    """Test handling of empty PDF."""
    with pytest.raises(ValueError, match="Empty or invalid"):
        extract_text_from_pdf(b"")


def test_pdf_without_text():
    """Test handling of PDF without text layer."""
    # Create a minimal PDF without text
    doc = fitz.open()
    page = doc.new_page()
    # Don't add any text, just create empty page
    pdf_bytes = doc.tobytes()
    doc.close()
    
    # This might not raise an error with PyMuPDF, but if we can't extract meaningful text,
    # the parser should handle it gracefully
    try:
        text = extract_text_from_pdf(pdf_bytes)
        # If we got empty text, parsing should still work but return empty list
        items = parse_lab_results(text)
        assert isinstance(items, list)
    except NoTextLayerError:
        # This is also acceptable
        pass


def test_parse_without_ref_range():
    """Test parsing of test without reference range."""
    test_text = "Colesterol No Hdl 160 mg/dL"
    
    pdf_bytes = create_test_pdf_with_text(test_text)
    text = extract_text_from_pdf(pdf_bytes)
    items = parse_lab_results(text)
    
    assert len(items) >= 1
    colesterol = next((item for item in items if "Colesterol" in item.analyte_name), None)
    if colesterol:
        assert abs(colesterol.value - 160) < 0.01
        assert colesterol.unit == "mg/dL"
        assert colesterol.ref_range is None


def test_save_to_database():
    """Test saving import data to database."""
    # Use in-memory SQLite
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    SessionLocal = get_session_factory(engine)
    
    # Create test data
    items = [
        ImportedLabItem(
            analyte_name="Glucosa",
            value=94.2,
            unit="mg/dL",
            ref_range="70 a 100",
        ),
        ImportedLabItem(
            analyte_name="Urea",
            value=74.8,
            unit="mg/dL",
            ref_range="19 a 44",
        ),
    ]
    
    import_data = ImportJson(
        patient_id="123",
        items=items,
        source_pdf="test.pdf",
    )
    
    # Save to database
    session = SessionLocal()
    try:
        # Extract patient_id from import_data for save_import_to_db
        patient_id = int(import_data.patient_id) if isinstance(import_data.patient_id, (int, str)) else None
        if patient_id is None:
            patient_id = 1  # Default for test
        items_count = save_import_to_db(session, import_data, patient_id)
        assert items_count == 2
        
        # Verify data in database
        results = session.query(LabResult).filter(LabResult.patient_id == "123").all()
        assert len(results) == 2
        
        glucosa = next((r for r in results if r.analyte_name == "Glucosa"), None)
        assert glucosa is not None
        assert abs(glucosa.value - 94.2) < 0.01
        assert glucosa.unit == "mg/dL"
        assert glucosa.ref_range == "70 a 100"
        assert glucosa.source_pdf == "test.pdf"
    finally:
        session.close()


def test_full_pdf_parsing():
    """Test full PDF parsing pipeline."""
    test_text = """Glucosa 94.2 mg/dL 70 a 100
Urea 74.8 mg/dL 19 a 44
Relacion BUN/CRE 14.75 10 a 20"""
    
    pdf_bytes = create_test_pdf_with_text(test_text)
    
    import_data = parse_pdf_to_import_json(
        pdf_bytes=pdf_bytes,
        patient_id="456",
        source_pdf="test_report.pdf",
    )
    
    assert import_data.patient_id == "456"
    assert import_data.source_pdf == "test_report.pdf"
    assert len(import_data.items) >= 2
    
    # Check for BUN/CRE
    bun_cre = next((item for item in import_data.items if "BUN/CRE" in item.analyte_name.upper()), None)
    assert bun_cre is not None, "BUN/CRE should be parsed"
    assert abs(bun_cre.value - 14.75) < 0.01

