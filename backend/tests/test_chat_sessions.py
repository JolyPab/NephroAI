from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.database import Base, User, ChatSession, ChatMessageRecord
from backend.main import app, get_current_user_id, get_db


def _setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _make_client(db, user_id):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    return TestClient(app)


def _make_user(db):
    user = User(email="sess@test.local", hashed_password="x", full_name="Test", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_and_list_sessions():
    db = _setup_db()
    user = _make_user(db)
    client = _make_client(db, user.id)

    # Create a session
    r = client.post("/api/chat/sessions", json={"title": "Primera consulta"})
    assert r.status_code == 200
    session_id = r.json()["id"]
    assert session_id > 0

    # List sessions
    r = client.get("/api/chat/sessions")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == session_id
    app.dependency_overrides.clear()
    db.close()


def test_get_session_messages():
    db = _setup_db()
    user = _make_user(db)
    session = ChatSession(user_id=user.id, title="Test")
    db.add(session)
    db.commit()
    db.refresh(session)
    db.add(ChatMessageRecord(session_id=session.id, role="user", content="Hola"))
    db.add(ChatMessageRecord(session_id=session.id, role="assistant", content="Hola!"))
    db.commit()

    client = _make_client(db, user.id)
    r = client.get(f"/api/chat/sessions/{session.id}/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    app.dependency_overrides.clear()
    db.close()


def test_delete_session_cascades_messages():
    db = _setup_db()
    user = _make_user(db)
    session = ChatSession(user_id=user.id, title="Del")
    db.add(session)
    db.commit()
    db.refresh(session)
    db.add(ChatMessageRecord(session_id=session.id, role="user", content="bye"))
    db.commit()

    client = _make_client(db, user.id)
    r = client.delete(f"/api/chat/sessions/{session.id}")
    assert r.status_code == 200

    remaining = db.query(ChatMessageRecord).filter_by(session_id=session.id).count()
    assert remaining == 0
    app.dependency_overrides.clear()
    db.close()


def test_cannot_access_other_users_session():
    db = _setup_db()
    user1 = _make_user(db)
    user2 = User(email="other@test.local", hashed_password="x", full_name="Other", is_active=True, is_doctor=False)
    db.add(user2)
    db.commit()
    db.refresh(user2)
    session = ChatSession(user_id=user1.id, title="Private")
    db.add(session)
    db.commit()
    db.refresh(session)

    client = _make_client(db, user2.id)
    r = client.get(f"/api/chat/sessions/{session.id}/messages")
    assert r.status_code == 404
    app.dependency_overrides.clear()
    db.close()
