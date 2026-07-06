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
from backend.database import AuditLog, Base, EmailVerificationCode, User


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def test_register_verify_and_login_flow(monkeypatch):
    db = _setup_db()
    sent_codes: list[str] = []

    def _fake_send(email: str, code: str, purpose: str = "email_verification"):
        assert email == "verify@example.com"
        assert purpose == "email_verification"
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
    assert login_exc.value.detail["code"] == "email_not_verified"
    assert login_exc.value.detail["email"] == "verify@example.com"
    assert len(sent_codes) == 1

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
    actions = {row.action for row in db.query(AuditLog).all()}
    assert "auth_register_started" in actions
    assert "auth_email_verify_failed" in actions
    assert "auth_email_verify_success" in actions
    assert "auth_login_success" in actions
    db.close()


def test_expired_registration_can_be_resumed(monkeypatch):
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(
        auth_routes,
        "send_verification_code_email",
        lambda _email, code, purpose="email_verification": sent_codes.append(code),
    )

    payload = UserRegister(
        email="resume@example.com",
        password="super-secret-123",
        full_name="Resume User",
        is_doctor=False,
    )
    asyncio.run(register(payload, db=db))
    first_code = db.query(EmailVerificationCode).one()
    first_code.expires_at = auth_routes.dt.datetime.utcnow() - auth_routes.dt.timedelta(minutes=1)
    first_code.created_at = auth_routes.dt.datetime.utcnow() - auth_routes.dt.timedelta(minutes=11)
    db.commit()

    response = asyncio.run(register(payload, db=db))

    assert response.status == "verification_required"
    assert response.email == "resume@example.com"
    assert len(sent_codes) == 2
    assert db.query(EmailVerificationCode).count() == 2
    assert first_code.used_at is not None
    actions = {row.action for row in db.query(AuditLog).all()}
    assert "auth_register_resumed" in actions
    db.close()


def test_login_with_expired_verification_code_sends_a_new_code(monkeypatch):
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(
        auth_routes,
        "send_verification_code_email",
        lambda _email, code, purpose="email_verification": sent_codes.append(code),
    )

    payload = UserRegister(
        email="login-resume@example.com",
        password="super-secret-123",
        full_name="Login Resume User",
        is_doctor=False,
    )
    asyncio.run(register(payload, db=db))
    first_code = db.query(EmailVerificationCode).one()
    first_code.expires_at = auth_routes.dt.datetime.utcnow() - auth_routes.dt.timedelta(minutes=1)
    first_code.created_at = auth_routes.dt.datetime.utcnow() - auth_routes.dt.timedelta(minutes=11)
    db.commit()

    with pytest.raises(HTTPException) as wrong_password_exc:
        asyncio.run(login(UserLogin(email=payload.email, password="wrong-password"), db=db))
    assert wrong_password_exc.value.status_code == 401
    assert len(sent_codes) == 1

    with pytest.raises(HTTPException) as login_exc:
        asyncio.run(login(UserLogin(email=payload.email, password=payload.password), db=db))

    assert login_exc.value.status_code == 403
    assert login_exc.value.detail["code"] == "email_not_verified"
    assert len(sent_codes) == 2
    assert db.query(EmailVerificationCode).count() == 2
    actions = {row.action for row in db.query(AuditLog).all()}
    assert "auth_email_verification_resumed" in actions
    db.close()


def test_resend_email_code_cooldown(monkeypatch):
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(
        auth_routes,
        "send_verification_code_email",
        lambda _email, code, purpose="email_verification": sent_codes.append(code),
    )

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


def test_verified_inactive_account_is_not_reactivated(monkeypatch):
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(
        auth_routes,
        "send_verification_code_email",
        lambda _email, code, purpose="email_verification": sent_codes.append(code),
    )
    payload = UserRegister(
        email="disabled@example.com",
        password="super-secret-123",
        full_name="Disabled User",
        is_doctor=False,
    )
    asyncio.run(register(payload, db=db))
    user = db.query(User).filter(User.email == payload.email).one()
    user.email_verified_at = auth_routes.dt.datetime.utcnow()
    user.is_active = False
    db.commit()

    with pytest.raises(HTTPException) as login_exc:
        asyncio.run(login(UserLogin(email=payload.email, password=payload.password), db=db))
    assert login_exc.value.status_code == 403
    assert login_exc.value.detail == "Esta cuenta está desactivada."

    with pytest.raises(HTTPException) as register_exc:
        asyncio.run(register(payload, db=db))
    assert register_exc.value.status_code == 400
    assert len(sent_codes) == 1
    assert user.is_active is False
    db.close()
