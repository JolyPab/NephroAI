import asyncio
from datetime import date, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.admin_routes import _admin_user, admin_overview
from backend.database import (
    AnalyticsEvent,
    Base,
    ChatSession,
    Payment,
    Subscription,
    User,
    V2Document,
)


def _db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_admin_access_uses_email_allowlist(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "owner@example.com, second@example.com")
    allowed = User(email="OWNER@example.com", hashed_password="hash")
    denied = User(email="patient@example.com", hashed_password="hash")

    assert _admin_user(allowed) is allowed
    with pytest.raises(HTTPException) as error:
        _admin_user(denied)
    assert error.value.status_code == 403


def test_overview_builds_funnel_without_exposing_full_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "owner@example.com")
    db = _db()
    try:
        admin = User(
            email="owner@example.com",
            hashed_password="hash",
            email_verified_at=datetime(2026, 7, 1),
            created_at=datetime(2026, 7, 1),
        )
        activated = User(
            email="activated@example.com",
            hashed_password="hash",
            email_verified_at=datetime(2026, 7, 17, 10),
            created_at=datetime(2026, 7, 17, 9),
        )
        checkout = User(
            email="checkout@example.com",
            hashed_password="hash",
            created_at=datetime(2026, 7, 18, 9),
        )
        db.add_all([admin, activated, checkout])
        db.flush()
        db.add_all(
            [
                AnalyticsEvent(
                    event_name="landing_view",
                    anonymous_id="visitor-one",
                    path="/",
                    created_at=datetime(2026, 7, 17, 8),
                ),
                AnalyticsEvent(
                    event_name="landing_view",
                    anonymous_id="visitor-two",
                    path="/",
                    created_at=datetime(2026, 7, 17, 8, 1),
                ),
                AnalyticsEvent(
                    event_name="auth_view",
                    anonymous_id="visitor-one",
                    path="/auth",
                    created_at=datetime(2026, 7, 17, 8, 2),
                ),
                V2Document(
                    user_id=activated.id,
                    document_hash="doc-1",
                    created_at=datetime(2026, 7, 17, 11),
                ),
                ChatSession(
                    user_id=activated.id,
                    title="Primera consulta",
                    created_at=datetime(2026, 7, 17, 12),
                ),
                Subscription(
                    user_id=checkout.id,
                    status="inactive",
                    created_at=datetime(2026, 7, 18, 10),
                ),
                Payment(
                    user_id=checkout.id,
                    status="pending",
                    amount=0,
                    currency="MXN",
                    created_at=datetime(2026, 7, 18, 10),
                ),
            ]
        )
        db.commit()

        result = asyncio.run(
            admin_overview(
                date_from=date(2026, 7, 16),
                date_to=date(2026, 7, 23),
                _=admin,
                db=db,
            )
        )

        assert result["funnel"] == {
            "visitors": 2,
            "access": 1,
            "registered": 2,
            "verified": 1,
            "activated": 1,
            "checkout": 1,
            "subscriptions": 0,
        }
        assert result["totals"]["users"] == 3
        assert result["recentUsers"][0]["email"] == "ch***@example.com"
        assert "checkout@example.com" not in str(result)
    finally:
        db.close()
