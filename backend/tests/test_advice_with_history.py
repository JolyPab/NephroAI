import asyncio
import datetime as dt
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, User, V2Document, V2Metric, ChatSession, ChatMessageRecord
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
    doc = V2Document(user_id=user.id, document_hash="h1", source_filename="a.pdf",
                     analysis_date=dt.datetime(2026, 1, 1), report_date=dt.datetime(2026, 1, 1))
    db.add(doc)
    db.flush()
    db.add(V2Metric(document_id=doc.id, analyte_key="CREATININE__SERUM__NUM",
                    raw_name="Creatinina", specimen="serum", context="random",
                    value_numeric=1.2, unit="mg/dL", page=1, evidence="Creat 1.2"))
    db.commit()
    return user


def test_advice_creates_session_when_none_provided():
    db = _setup_db()
    user = _seed_user_with_metric(db)
    with patch("backend.main._openai_chat_with_tools", return_value="respuesta de prueba"), \
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

    with patch("backend.main._openai_chat_with_tools", return_value="bien") as mock_llm, \
         patch("backend.main._get_redis", return_value=None):
        asyncio.run(get_advice(
            req=AdviceRequest(question="Que significa creatinina alta?", session_id=session.id),
            user_id=user.id, db=db,
        ))
    # History passed to LLM must include prior messages
    call_args = mock_llm.call_args
    messages_arg = call_args[0][1]  # second positional arg
    roles = [m["role"] for m in messages_arg]
    assert "user" in roles
    assert "assistant" in roles
    db.close()
