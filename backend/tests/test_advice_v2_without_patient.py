import asyncio
import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, User, V2Document, V2Metric
from backend.main import AdviceRequest, get_advice


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def test_advice_works_with_v2_data_when_patient_row_missing(monkeypatch):
    db = _setup_db()

    user = User(email="advice-v2@test.local", hashed_password="x", full_name="Advice User", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    doc = V2Document(
        user_id=user.id,
        document_hash="advice-doc-hash",
        source_filename="advice.pdf",
        analysis_date=dt.datetime(2026, 2, 1),
        report_date=dt.datetime(2026, 2, 1),
    )
    db.add(doc)
    db.flush()
    db.add(
        V2Metric(
            document_id=doc.id,
            analyte_key="ALT_SERUM",
            raw_name="ALT (TGP)",
            specimen="serum",
            context="random",
            value_numeric=36.0,
            value_text=None,
            unit="U/L",
            reference_json={"type": "max", "threshold": 41},
            page=1,
            evidence="ALT (TGP) 36 U/L",
        )
    )
    db.commit()

    monkeypatch.setattr("backend.main._openai_chat_completion", lambda *_args, **_kwargs: "ok")

    response = asyncio.run(
        get_advice(
            req=AdviceRequest(question="Resume mis tendencias", language="es"),
            user_id=user.id,
            db=db,
        )
    )

    assert response.answer == "ok"
    assert response.disclaimer is True
    assert len(response.usedMetrics) >= 1
    assert response.usedMetrics[0].name == "ALT_SERUM"

    db.close()
