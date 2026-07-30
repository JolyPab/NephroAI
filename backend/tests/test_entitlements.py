import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, Subscription, User
from backend.entitlements import (
    get_ai_allowance,
    get_upload_allowance,
    refund_ai_message,
    refund_free_upload,
    reserve_ai_message,
    reserve_free_upload,
)


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_free_upload_allowance_reserves_and_refunds_atomically():
    db = _setup_db()
    user = User(email="free@test.local", hashed_password="x", is_active=True, is_doctor=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    assert get_upload_allowance(db, user.id).remaining == 2
    assert reserve_free_upload(db, user.id).remaining == 1
    assert reserve_free_upload(db, user.id).remaining == 0
    assert reserve_free_upload(db, user.id) is None

    refund_free_upload(db, user.id)
    assert get_upload_allowance(db, user.id).remaining == 1
    db.close()


def test_active_subscription_has_20_messages_per_calendar_month(monkeypatch):
    monkeypatch.delenv("AI_MONTHLY_MESSAGE_LIMIT", raising=False)
    db = _setup_db()
    user = User(email="paid@test.local", hashed_password="x", is_active=True, is_doctor=False)
    db.add(user)
    db.flush()
    db.add(Subscription(user_id=user.id, status="active"))
    db.commit()
    db.refresh(user)

    now = dt.datetime(2026, 7, 31, 12, 0)
    for expected_remaining in range(19, -1, -1):
        allowance = reserve_ai_message(db, user.id, now=now)
        assert allowance is not None
        assert allowance.remaining == expected_remaining
    assert reserve_ai_message(db, user.id, now=now) is None

    next_month = get_ai_allowance(db, user.id, now=dt.datetime(2026, 8, 1, 0, 0))
    assert next_month.limit == 20
    assert next_month.remaining == 20
    db.close()


def test_trial_has_five_messages_for_the_whole_trial(monkeypatch):
    monkeypatch.delenv("AI_TRIAL_MESSAGE_LIMIT", raising=False)
    db = _setup_db()
    user = User(email="trial@test.local", hashed_password="x", is_active=True, is_doctor=False)
    db.add(user)
    db.flush()
    db.add(
        Subscription(
            user_id=user.id,
            status="trialing",
            trial_end=dt.datetime(2026, 8, 7),
        )
    )
    db.commit()
    db.refresh(user)

    reserved = [reserve_ai_message(db, user.id, now=dt.datetime(2026, 7, 31)) for _ in range(5)]
    assert all(item is not None for item in reserved)
    assert reserved[-1].remaining == 0
    assert reserve_ai_message(db, user.id, now=dt.datetime(2026, 8, 1)) is None

    refund_ai_message(db, user.id, reserved[-1].period_key)
    assert get_ai_allowance(db, user.id, now=dt.datetime(2026, 8, 1)).remaining == 1
    db.close()
