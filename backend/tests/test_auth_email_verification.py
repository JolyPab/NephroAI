import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import auth_routes
from backend.auth_routes import (
    ResendEmailCodeRequest,
    UserLogin,
    UserRegister,
    VerifyEmailRequest,
    login,
    register,
    resend_email_code,
    verify_email,
)
from backend.database import Base, EmailVerificationCode, User


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def test_register_verify_and_login_flow(monkeypatch):
    db = _setup_db()
    sent_codes: list[str] = []

    def _fake_send(email: str, code: str):
        assert email == "verify@example.com"
        sent_codes.append(code)

    monkeypatch.setattr(auth_routes, "send_verification_code_email", _fake_send)

    reg_payload = UserRegister(
        email="verify@example.com",
        password="super-secret-123",
        full_name="Verify User",
        is_doctor=False,
    )
    reg_response = asyncio.run(register(reg_payload, db=db))
    assert reg_response.status == "verification_required"
    assert len(sent_codes) == 1

    user = db.query(User).filter(User.email == "verify@example.com").first()
    assert user is not None
    assert user.is_active is False
    assert user.email_verified_at is None

    with pytest.raises(HTTPException) as login_exc:
        asyncio.run(login(UserLogin(email="verify@example.com", password="super-secret-123"), db=db))
    assert login_exc.value.status_code == 403

    with pytest.raises(HTTPException) as wrong_code_exc:
        asyncio.run(verify_email(VerifyEmailRequest(email="verify@example.com", code="000000"), db=db))
    assert wrong_code_exc.value.status_code == 400

    verify_response = asyncio.run(
        verify_email(VerifyEmailRequest(email="verify@example.com", code=sent_codes[0]), db=db)
    )
    assert verify_response.accessToken
    assert verify_response.user.email_verified is True
    assert verify_response.user.is_active is True

    login_response = asyncio.run(login(UserLogin(email="verify@example.com", password="super-secret-123"), db=db))
    assert login_response.accessToken
    assert login_response.user.email_verified is True
    db.close()


def test_resend_email_code_cooldown(monkeypatch):
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda _email, code: sent_codes.append(code))

    reg_payload = UserRegister(
        email="cooldown@example.com",
        password="super-secret-123",
        full_name="Cooldown User",
        is_doctor=False,
    )
    asyncio.run(register(reg_payload, db=db))

    with pytest.raises(HTTPException) as resend_exc:
        asyncio.run(resend_email_code(ResendEmailCodeRequest(email="cooldown@example.com"), db=db))
    assert resend_exc.value.status_code == 429
    assert len(sent_codes) == 1
    assert db.query(EmailVerificationCode).count() == 1
    db.close()
