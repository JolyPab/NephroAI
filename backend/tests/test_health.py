import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import main
from backend.database import Base


def test_readiness_checks_database_and_skips_redis_in_development(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(main, "SessionLocal", session_local)
    monkeypatch.setenv("REQUIRE_REDIS_HEALTH", "false")

    response = asyncio.run(main.readiness())
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload == {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "skipped",
        },
    }
