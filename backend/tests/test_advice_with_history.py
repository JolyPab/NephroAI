import asyncio
import datetime as dt
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import AiUsagePeriod, AuditLog, Base, User, V2Document, V2Metric, ChatSession, ChatMessageRecord, Subscription
from backend.chat_routes import AI_SCOPE_REFUSAL_ES, _build_positive_trend_notes
from backend.main import AdviceRequest, get_advice


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed_user_with_metric(db):
    user = User(email="hist@test.local", hashed_password="x", full_name="Ana García", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(Subscription(user_id=user.id, stripe_customer_id="cus_test_123", plan_id="price_test", status="active"))
    recent_date = dt.datetime.utcnow() - dt.timedelta(days=10)
    doc = V2Document(user_id=user.id, document_hash="h1", source_filename="a.pdf",
                     analysis_date=recent_date, report_date=recent_date)
    db.add(doc)
    db.flush()
    db.add(V2Metric(document_id=doc.id, analyte_key="CREATININE__SERUM__NUM",
                    raw_name="Creatinina", specimen="serum", context="random",
                    value_numeric=1.2, unit="mg/dL", page=1, evidence="Creat 1.2"))
    db.commit()
    return user


def _seed_user_with_two_metrics(db):
    user = User(email="trend@test.local", hashed_password="x", full_name="Ana García", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(Subscription(user_id=user.id, stripe_customer_id="cus_test_123", plan_id="price_test", status="active"))

    now = dt.datetime.utcnow()
    old_date = now - dt.timedelta(days=60)
    new_date = now - dt.timedelta(days=10)
    old_doc = V2Document(
        user_id=user.id,
        document_hash="trend-old",
        source_filename="old.pdf",
        analysis_date=old_date,
        report_date=old_date,
    )
    new_doc = V2Document(
        user_id=user.id,
        document_hash="trend-new",
        source_filename="new.pdf",
        analysis_date=new_date,
        report_date=new_date,
    )
    db.add_all([old_doc, new_doc])
    db.flush()
    db.add_all([
        V2Metric(document_id=old_doc.id, analyte_key="GLUCOSE__SERUM__NUM",
                 raw_name="Glucosa", specimen="serum", context="random",
                 value_numeric=156.0, unit="mg/dL", reference_json={"type": "range", "min": 70, "max": 110},
                 page=1, evidence="Glucosa 156"),
        V2Metric(document_id=new_doc.id, analyte_key="GLUCOSE__SERUM__NUM",
                 raw_name="Glucosa", specimen="serum", context="random",
                 value_numeric=104.0, unit="mg/dL", reference_json={"type": "range", "min": 70, "max": 110},
                 page=1, evidence="Glucosa 104"),
        V2Metric(document_id=old_doc.id, analyte_key="CREATININE__SERUM__NUM",
                 raw_name="Creatinina", specimen="serum", context="random",
                 value_numeric=1.2, unit="mg/dL", reference_json={"type": "max", "threshold": 1.3},
                 page=1, evidence="Creatinina 1.2"),
        V2Metric(document_id=new_doc.id, analyte_key="CREATININE__SERUM__NUM",
                 raw_name="Creatinina", specimen="serum", context="random",
                 value_numeric=1.2, unit="mg/dL", reference_json={"type": "max", "threshold": 1.3},
                 page=1, evidence="Creatinina 1.2"),
    ])
    db.commit()
    return user


def test_positive_trend_notes_encourage_real_improvement():
    notes = _build_positive_trend_notes({
        "GLUCOSE__SERUM__NUM": [
            {"value": 104.0, "unit": "mg/dL", "ref_min": 70, "ref_max": 110},
            {"value": 156.0, "unit": "mg/dL", "ref_min": 70, "ref_max": 110},
        ]
    })

    assert len(notes) == 1
    assert "Buen progreso" in notes[0]
    assert "dentro del rango" in notes[0]


def test_advice_creates_session_when_none_provided():
    db = _setup_db()
    user = _seed_user_with_metric(db)
    with patch("backend.chat_routes._openai_chat_with_tools", return_value="respuesta de prueba"), \
         patch("backend.main._get_redis", return_value=None):
        response = asyncio.run(get_advice(
            req=AdviceRequest(question="Como esta mi creatinina?"),
            user_id=user.id, db=db,
        ))
    assert response.answer == "respuesta de prueba"
    assert response.session_id is not None
    session = db.query(ChatSession).filter_by(user_id=user.id).first()
    assert session is not None
    assert "creatinina" in (session.title or "").lower()
    actions = {row.action for row in db.query(AuditLog).all()}
    assert "patient_ai_context_built" in actions
    assert "patient_ai_chat_completed" in actions
    db.close()


def test_advice_reuses_existing_session_and_saves_messages():
    db = _setup_db()
    user = _seed_user_with_metric(db)
    session = ChatSession(user_id=user.id, title="")
    db.add(session)
    db.commit()
    db.refresh(session)
    db.add(ChatMessageRecord(session_id=session.id, role="user", content="Hola"))
    db.add(ChatMessageRecord(session_id=session.id, role="assistant", content="Hola, en que puedo ayudarte?"))
    db.commit()

    with patch("backend.chat_routes._openai_chat_with_tools", return_value="bien") as mock_llm, \
         patch("backend.main._get_redis", return_value=None):
        asyncio.run(get_advice(
            req=AdviceRequest(question="Que significa creatinina alta?", session_id=session.id),
            user_id=user.id, db=db,
        ))
    # History passed to LLM must include prior messages
    call_args = mock_llm.call_args
    messages_arg = call_args.args[1]  # second positional arg
    roles = [m["role"] for m in messages_arg]
    assert "user" in roles
    assert "assistant" in roles
    assert len(messages_arg) >= 3
    db.close()


def test_advice_requires_active_subscription():
    db = _setup_db()
    user = User(email="locked@test.local", hashed_password="x", full_name="Ana", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_advice(
            req=AdviceRequest(question="Como esta mi creatinina?"),
            user_id=user.id, db=db,
        ))

    assert exc.value.status_code == 403
    assert "suscripción activa" in exc.value.detail
    db.close()


def test_chart_advice_includes_positive_trend_context_for_selected_metric():
    db = _setup_db()
    user = _seed_user_with_two_metrics(db)

    with patch("backend.chat_routes._openai_chat_with_tools", return_value="ok") as mock_llm, \
         patch("backend.main._get_redis", return_value=None):
        asyncio.run(get_advice(
            req=AdviceRequest(
                question="Dame un breve analisis de Glucosa",
                metric_names=["GLUCOSE__SERUM__NUM", "Glucosa"],
                language="es",
            ),
            user_id=user.id,
            db=db,
        ))

    messages_arg = mock_llm.call_args.args[1]
    prompt = messages_arg[-1]["content"]
    assert "Tendencias positivas detectadas" in prompt
    assert "GLUCOSE__SERUM__NUM" in prompt
    assert "Buen progreso" in prompt
    assert "CREATININE__SERUM__NUM" not in prompt
    db.close()


def test_non_persistent_chart_advice_does_not_create_chat_session():
    db = _setup_db()
    user = _seed_user_with_two_metrics(db)

    with patch("backend.chat_routes._openai_chat_with_tools", return_value="ok"), \
         patch("backend.main._get_redis", return_value=None):
        response = asyncio.run(get_advice(
            req=AdviceRequest(
                question="Dame un breve analisis de Glucosa",
                metric_names=["GLUCOSE__SERUM__NUM", "Glucosa"],
                language="es",
                persist=False,
            ),
            user_id=user.id,
            db=db,
        ))

    assert response.session_id is None
    assert db.query(ChatSession).filter_by(user_id=user.id).count() == 0
    assert db.query(ChatMessageRecord).count() == 0
    db.close()


def test_obvious_programming_request_is_rejected_without_using_quota():
    db = _setup_db()
    user = _seed_user_with_metric(db)

    with patch("backend.chat_routes._openai_chat_with_tools") as mock_llm:
        response = asyncio.run(get_advice(
            req=AdviceRequest(question="Сделай мне скрипт Python для обработки файлов"),
            user_id=user.id,
            db=db,
        ))

    assert response.answer == AI_SCOPE_REFUSAL_ES
    assert response.scope_rejected is True
    assert response.ai_messages_remaining == 20
    mock_llm.assert_not_called()
    assert db.query(AiUsagePeriod).count() == 0
    assert db.query(AuditLog).filter_by(action="patient_ai_scope_rejected").count() == 1
    db.close()


def test_monthly_chat_limit_returns_structured_429():
    db = _setup_db()
    user = _seed_user_with_metric(db)
    now = dt.datetime.utcnow()
    month_start = dt.datetime(now.year, now.month, 1)
    db.add(
        AiUsagePeriod(
            user_id=user.id,
            period_key=f"month:{month_start:%Y-%m}",
            period_start=month_start,
            messages_used=20,
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_advice(
            req=AdviceRequest(question="¿Cómo está mi creatinina actualmente?"),
            user_id=user.id,
            db=db,
        ))

    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "ai_monthly_limit_reached"
    assert exc.value.detail["remaining"] == 0
    db.close()
