import asyncio
import datetime as dt

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import auth_routes
from backend.auth_routes import (
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    ResetPasswordRequest,
    UserRegister,
    UserLogin,
    VerifyEmailRequest,
    forgot_password,
    verify_reset_code,
    reset_password,
    register,
    verify_email,
    login,
)
from backend.database import Base, EmailVerificationCode, User


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _register_and_verify(email: str, password: str, db, sent_codes: list[str]):
    """Helper: register + verify email."""
    asyncio.run(register(UserRegister(email=email, password=password, full_name="User", is_doctor=False), db=db))
    reg_code = sent_codes[-1]
    asyncio.run(verify_email(VerifyEmailRequest(email=email, code=reg_code), db=db))


def test_purpose_column_isolation(monkeypatch):
    """A password_reset code must not be rate-limited by email_verification cooldown."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    asyncio.run(register(UserRegister(email="iso@example.com", password="password123", full_name="Iso", is_doctor=False), db=db))
    assert len(sent_codes) == 1

    asyncio.run(forgot_password(ForgotPasswordRequest(email="iso@example.com"), db=db))
    assert len(sent_codes) == 2

    codes = db.query(EmailVerificationCode).filter(EmailVerificationCode.email == "iso@example.com").all()
    purposes = {c.purpose for c in codes}
    assert "email_verification" in purposes
    assert "password_reset" in purposes


def test_forgot_password_unknown_email(monkeypatch):
    """Unknown email must return 200 (no account enumeration)."""
    db = _setup_db()
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: None)
    resp = asyncio.run(forgot_password(ForgotPasswordRequest(email="nobody@example.com"), db=db))
    assert resp.status == "ok"


def test_full_reset_flow(monkeypatch):
    """Happy path: forgot -> verify code -> reset password -> login with new password."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("reset@example.com", "old-password-1", db, sent_codes)

    asyncio.run(forgot_password(ForgotPasswordRequest(email="reset@example.com"), db=db))
    reset_code = sent_codes[-1]

    token_resp = asyncio.run(verify_reset_code(
        VerifyResetCodeRequest(email="reset@example.com", code=reset_code), db=db
    ))
    assert token_resp.reset_token

    status_resp = asyncio.run(reset_password(
        ResetPasswordRequest(reset_token=token_resp.reset_token, new_password="new-password-2"), db=db
    ))
    assert status_resp.status == "ok"

    with pytest.raises(HTTPException) as exc:
        asyncio.run(login(UserLogin(email="reset@example.com", password="old-password-1"), db=db))
    assert exc.value.status_code == 401

    auth_resp = asyncio.run(login(UserLogin(email="reset@example.com", password="new-password-2"), db=db))
    assert auth_resp.accessToken is not None


def test_reset_code_wrong_code(monkeypatch):
    """Wrong code increments attempts and raises 400."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("wrong@example.com", "password123", db, sent_codes)
    asyncio.run(forgot_password(ForgotPasswordRequest(email="wrong@example.com"), db=db))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_reset_code(
            VerifyResetCodeRequest(email="wrong@example.com", code="000000"), db=db
        ))
    assert exc.value.status_code == 400

    code_row = (
        db.query(EmailVerificationCode)
        .filter(EmailVerificationCode.email == "wrong@example.com",
                EmailVerificationCode.purpose == "password_reset")
        .first()
    )
    assert code_row.attempts == 1


def test_reset_code_expired(monkeypatch):
    """Expired reset code raises 400."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("expired@example.com", "password123", db, sent_codes)
    asyncio.run(forgot_password(ForgotPasswordRequest(email="expired@example.com"), db=db))

    code_row = (
        db.query(EmailVerificationCode)
        .filter(EmailVerificationCode.email == "expired@example.com",
                EmailVerificationCode.purpose == "password_reset")
        .first()
    )
    code_row.expires_at = dt.datetime.utcnow() - dt.timedelta(minutes=1)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_reset_code(
            VerifyResetCodeRequest(email="expired@example.com", code=sent_codes[-1]), db=db
        ))
    assert exc.value.status_code == 400


def test_reset_token_wrong_purpose(monkeypatch):
    """A regular login JWT must be rejected by reset-password endpoint."""
    db = _setup_db()
    from backend.auth import create_access_token
    bad_token = create_access_token(data={"sub": "1"})

    with pytest.raises(HTTPException) as exc:
        asyncio.run(reset_password(
            ResetPasswordRequest(reset_token=bad_token, new_password="new-password-x"), db=db
        ))
    assert exc.value.status_code == 400


def test_reset_codes_invalidated_after_reset(monkeypatch):
    """All active reset codes are marked used after a successful reset."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("cleanup@example.com", "password123", db, sent_codes)
    asyncio.run(forgot_password(ForgotPasswordRequest(email="cleanup@example.com"), db=db))
    reset_code = sent_codes[-1]

    token_resp = asyncio.run(verify_reset_code(
        VerifyResetCodeRequest(email="cleanup@example.com", code=reset_code), db=db
    ))
    asyncio.run(reset_password(
        ResetPasswordRequest(reset_token=token_resp.reset_token, new_password="brand-new-pass"), db=db
    ))

    active_codes = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == "cleanup@example.com",
            EmailVerificationCode.purpose == "password_reset",
            EmailVerificationCode.used_at.is_(None),
        )
        .count()
    )
    assert active_codes == 0
