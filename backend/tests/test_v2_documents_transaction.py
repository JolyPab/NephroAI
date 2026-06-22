import asyncio
import io

import pytest
import fitz
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, User, V2Document, V2Metric
from backend.v2_routes import create_v2_document, _prepare_pdf_bytes_for_extraction
from backend.v2.schemas import (
    Context,
    ImportV2,
    MetricV2,
    ReferenceType,
    ReferenceV2,
    Specimen,
)


def _build_payload() -> ImportV2:
    return ImportV2(
        analysis_date=None,
        report_date=None,
        patient_age=30,
        patient_sex="F",
        metrics=[
            MetricV2(
                raw_name="CREATININA",
                analyte_key="CREATININE_SERUM",
                specimen=Specimen.serum,
                context=Context.random,
                value_numeric=1.1,
                value_text=None,
                unit="mg/dL",
                reference=ReferenceV2(
                    type=ReferenceType.range,
                    min=0.7,
                    max=1.3,
                    threshold=None,
                    categories=None,
                    stages=None,
                    ref_text_raw="0.7 a 1.3",
                ),
                evidence="CREATININA 1.1 mg/dL 0.7 a 1.3",
                page=1,
            )
        ],
        warnings=[],
    )


def _make_upload() -> UploadFile:
    return UploadFile(filename="tx-test.pdf", file=io.BytesIO(b"%PDF-1.4 fake"))


def _make_password_pdf(password: str = "cedula123") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "CREATININA 1.1 mg/dL")
    out = io.BytesIO()
    doc.save(
        out,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw=password,
    )
    doc.close()
    return out.getvalue()


def test_prepare_pdf_bytes_requires_password_for_encrypted_pdf():
    encrypted = _make_password_pdf()

    with pytest.raises(HTTPException) as exc:
        _prepare_pdf_bytes_for_extraction(encrypted)

    assert exc.value.status_code == 423
    assert exc.value.detail["code"] == "pdf_password_required"


def test_prepare_pdf_bytes_rejects_invalid_pdf_password():
    encrypted = _make_password_pdf()

    with pytest.raises(HTTPException) as exc:
        _prepare_pdf_bytes_for_extraction(encrypted, "wrong")

    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "pdf_password_invalid"


def test_prepare_pdf_bytes_unlocks_encrypted_pdf_with_password():
    encrypted = _make_password_pdf()

    unlocked = _prepare_pdf_bytes_for_extraction(encrypted, "cedula123")
    doc = fitz.open(stream=unlocked, filetype="pdf")
    try:
        assert not doc.needs_pass
        assert "CREATININA" in doc[0].get_text()
    finally:
        doc.close()


def test_create_v2_document_rolls_back_and_recovers(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    user = User(email="tx@test.local", hashed_password="x", full_name="Tx User", is_active=True, is_doctor=False)
    db.add(user)
    db.flush()
    from backend.database import Subscription
    sub = Subscription(user_id=user.id, stripe_customer_id="cus_test_123", plan_id="price_monthly", status="active")
    db.add(sub)
    db.commit()
    db.refresh(user)

    payload = _build_payload()

    async def fake_extract_v2(_pdf_bytes: bytes) -> ImportV2:
        return payload

    monkeypatch.setattr("backend.v2_routes.extract_v2", fake_extract_v2)

    original_flush = db.flush
    state = {"fail_once": True}

    def flush_fail_once(*args, **kwargs):
        if state["fail_once"]:
            state["fail_once"] = False
            raise RuntimeError("simulated failure after db.add(doc)")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", flush_fail_once)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(create_v2_document(file=_make_upload(), user_id=user.id, db=db))
    assert exc.value.status_code == 500

    # No partial persistence after failure.
    assert db.query(V2Document).count() == 0
    assert db.query(V2Metric).count() == 0

    # Subsequent request succeeds.
    created = asyncio.run(create_v2_document(file=_make_upload(), user_id=user.id, db=db))
    assert "document_id" in created
    assert created["num_metrics"] == 1
    assert db.query(V2Document).count() == 1
    assert db.query(V2Metric).count() == 1

    # Repeating request returns dedupe response and still succeeds.
    duplicate = asyncio.run(create_v2_document(file=_make_upload(), user_id=user.id, db=db))
    assert duplicate.get("status") == "duplicate"
    assert db.query(V2Document).count() == 1
    assert db.query(V2Metric).count() == 1

    db.close()
