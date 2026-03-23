from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from backend.database import Base, User, PatientMemory
from backend.main import app, get_current_user_id, get_db


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _make_user(db):
    u = User(email="mem@test.local", hashed_password="x", full_name="Mem", is_active=True, is_doctor=False)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _make_client(db, user_id):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    return TestClient(app)


def test_list_memory_facts():
    db = _setup_db()
    user = _make_user(db)
    db.add(PatientMemory(user_id=user.id, fact="Toma metformina", category="medical"))
    db.add(PatientMemory(user_id=user.id, fact="No le gustan los consejos sobre agua", category="preference"))
    db.commit()

    client = _make_client(db, user.id)
    r = client.get("/api/chat/memory")
    assert r.status_code == 200
    facts = r.json()
    assert len(facts) == 2
    categories = {f["category"] for f in facts}
    assert "medical" in categories
    app.dependency_overrides.clear()
    db.close()


def test_delete_memory_fact():
    db = _setup_db()
    user = _make_user(db)
    mem = PatientMemory(user_id=user.id, fact="Dato a borrar", category="medical")
    db.add(mem); db.commit(); db.refresh(mem)

    client = _make_client(db, user.id)
    r = client.delete(f"/api/chat/memory/{mem.id}")
    assert r.status_code == 200
    assert db.query(PatientMemory).filter_by(id=mem.id).first() is None
    app.dependency_overrides.clear()
    db.close()


def test_cannot_delete_other_users_memory():
    db = _setup_db()
    user1 = _make_user(db)
    user2 = User(email="other2@test.local", hashed_password="x", full_name="Other", is_active=True, is_doctor=False)
    db.add(user2); db.commit(); db.refresh(user2)
    mem = PatientMemory(user_id=user1.id, fact="Privado", category="medical")
    db.add(mem); db.commit(); db.refresh(mem)

    client = _make_client(db, user2.id)
    r = client.delete(f"/api/chat/memory/{mem.id}")
    assert r.status_code == 404
    app.dependency_overrides.clear()
    db.close()
