import asyncio
import datetime as dt

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, User, V2Document, V2Metric
from backend.main import delete_v2_document, list_v2_documents


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def test_list_v2_documents_and_delete_cascades_metrics():
    db = _setup_db()
    user = User(email="docs@test.local", hashed_password="x", full_name="Docs User", is_active=True, is_doctor=False)
    other = User(email="other@test.local", hashed_password="x", full_name="Other User", is_active=True, is_doctor=False)
    db.add_all([user, other])
    db.commit()
    db.refresh(user)
    db.refresh(other)

    doc1 = V2Document(
        user_id=user.id,
        document_hash="hash-1",
        source_filename="lab-1.pdf",
        analysis_date=dt.datetime(2025, 1, 10),
        report_date=dt.datetime(2025, 1, 11),
    )
    doc2 = V2Document(
        user_id=user.id,
        document_hash="hash-2",
        source_filename="lab-2.pdf",
        analysis_date=dt.datetime(2025, 2, 10),
        report_date=dt.datetime(2025, 2, 11),
    )
    foreign_doc = V2Document(
        user_id=other.id,
        document_hash="hash-3",
        source_filename="other.pdf",
    )
    db.add_all([doc1, doc2, foreign_doc])
    db.flush()
    db.add_all(
        [
            V2Metric(
                document_id=doc1.id,
                analyte_key="ALT_SERUM",
                raw_name="ALT",
                specimen="serum",
                context="random",
                value_numeric=32.0,
                value_text=None,
                unit="U/L",
                reference_json=None,
                page=1,
                evidence="ALT 32",
            ),
            V2Metric(
                document_id=doc2.id,
                analyte_key="AST_SERUM",
                raw_name="AST",
                specimen="serum",
                context="random",
                value_numeric=25.0,
                value_text=None,
                unit="U/L",
                reference_json=None,
                page=1,
                evidence="AST 25",
            ),
            V2Metric(
                document_id=doc2.id,
                analyte_key="CREATININE_SERUM",
                raw_name="CREATININA",
                specimen="serum",
                context="random",
                value_numeric=1.1,
                value_text=None,
                unit="mg/dL",
                reference_json=None,
                page=1,
                evidence="CREATININA 1.1",
            ),
        ]
    )
    db.commit()

    listed = asyncio.run(list_v2_documents(user_id=user.id, db=db))
    assert len(listed) == 2
    assert listed[0]["id"] == doc2.id
    assert listed[0]["num_metrics"] == 2
    assert listed[1]["id"] == doc1.id
    assert listed[1]["num_metrics"] == 1

    deleted = asyncio.run(delete_v2_document(document_id=doc2.id, user_id=user.id, db=db))
    assert deleted["status"] == "deleted"
    assert deleted["num_metrics_deleted"] == 2
    assert db.query(V2Document).filter(V2Document.id == doc2.id).count() == 0
    assert db.query(V2Metric).filter(V2Metric.document_id == doc2.id).count() == 0

    # Foreign user's doc remains untouched.
    assert db.query(V2Document).filter(V2Document.id == foreign_doc.id).count() == 1
    db.close()


def test_delete_v2_document_not_found():
    db = _setup_db()
    user = User(email="missing@test.local", hashed_password="x", full_name="Missing User", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(delete_v2_document(document_id="no-such-doc", user_id=user.id, db=db))
    assert exc.value.status_code == 404
    db.close()
