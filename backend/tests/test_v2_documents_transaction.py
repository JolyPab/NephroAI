import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, User, V2Document, V2Metric
from backend.main import create_v2_document
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


def test_create_v2_document_rolls_back_and_recovers(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    user = User(email="tx@test.local", hashed_password="x", full_name="Tx User", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    payload = _build_payload()

    async def fake_extract_v2(_pdf_bytes: bytes) -> ImportV2:
        return payload

    monkeypatch.setattr("backend.main.extract_v2", fake_extract_v2)

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
