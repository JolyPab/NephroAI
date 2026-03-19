# Password Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 3-step password-reset flow (email → OTP code → new password) accessible from the login page.

**Architecture:** Reuse the existing `EmailVerificationCode` table by adding a `purpose` column; add 3 new FastAPI endpoints in `auth_routes.py`; extend the Angular auth-page component with 3 new modes.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, SQLite/PostgreSQL, Angular 20, `@ngx-translate/core`, pytest, `asyncio.run()` for sync tests.

**Spec:** `docs/superpowers/specs/2026-03-19-password-reset-design.md`

**Working directory note:** All `git` commands must run from the repo root `c:\Users\jolypab\Documents\CODE\medic`. pytest commands run from the repo root too (prefix with `cd backend &&` only when needed, then `cd ..` back before git ops, or just use absolute paths).

---

## File Map

| File | Change |
|------|--------|
| `backend/database.py` | Add `purpose` column to `EmailVerificationCode` model; add `ensure_email_code_purpose_column()`; call from `init_db()` |
| `backend/auth_routes.py` | Add `purpose` param to `_create_verification_code()`; add 3 request models + 2 response models; add 3 endpoints |
| `backend/tests/test_auth_password_reset.py` | New file — full flow tests + edge cases |
| `frontend/src/app/core/services/auth.service.ts` | Add `forgotPassword()`, `verifyResetCode()`, `resetPassword()` |
| `frontend/src/app/features/auth/pages/auth-page/auth-page.component.ts` | Extend mode type; add forms; add submit/resend/nav methods |
| `frontend/src/app/features/auth/pages/auth-page/auth-page.component.html` | Add forgot link on login form; add 3 new form sections; fix header buttons |
| `frontend/src/assets/i18n/es.json` | Add password-reset i18n keys |
| `frontend/src/assets/i18n/en.json` | Add password-reset i18n keys |
| `frontend/src/assets/i18n/ru.json` | Add password-reset i18n keys |

---

## Task 1: DB — add `purpose` column to `EmailVerificationCode`

**Files:**
- Modify: `backend/database.py`

- [ ] **Step 1: Add `purpose` column to the SQLAlchemy model**

In `backend/database.py`, add `purpose` field to `EmailVerificationCode` (after the `used_at` line):

```python
purpose = Column(String(32), nullable=False, default="email_verification")
```

- [ ] **Step 2: Add `ensure_email_code_purpose_column()` function**

Add this function after `ensure_users_columns()` in `backend/database.py`:

```python
def ensure_email_code_purpose_column(engine) -> list[str]:
    """Add purpose column to email_verification_codes if missing."""
    try:
        inspector = inspect(engine)
        if "email_verification_codes" not in inspector.get_table_names():
            return []
        existing = {col["name"] for col in inspector.get_columns("email_verification_codes")}
        if "purpose" in existing:
            return []
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE email_verification_codes "
                "ADD COLUMN purpose VARCHAR(32) NOT NULL DEFAULT 'email_verification'"
            ))
        return ["purpose"]
    except Exception as exc:
        print(f"[WARN] Could not ensure email_verification_codes.purpose: {exc}")
        return []
```

- [ ] **Step 3: Call from `init_db()`**

Replace the existing `init_db()` function:

```python
def init_db(engine):
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    added_columns = ensure_lab_results_columns(engine)
    user_added_columns = ensure_users_columns(engine)
    code_added_columns = ensure_email_code_purpose_column(engine)
    if added_columns:
        print(f"[DB] added columns: {', '.join(added_columns)}")
    if user_added_columns:
        print(f"[DB] added user columns: {', '.join(user_added_columns)}")
    if code_added_columns:
        print(f"[DB] added email_code columns: {', '.join(code_added_columns)}")
```

- [ ] **Step 4: Commit (from repo root)**

```bash
git add backend/database.py && git commit -m "feat: add purpose column to EmailVerificationCode"
```

---

## Task 2: Backend — update `_create_verification_code()` + add request models

**Files:**
- Modify: `backend/auth_routes.py`
- Create: `backend/tests/test_auth_password_reset.py`

- [ ] **Step 1: Write the failing test for purpose isolation**

Create `backend/tests/test_auth_password_reset.py`:

```python
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


def _make_user():
    return UserRegister(
        email="test@test.local",
        password="password123",
        full_name="Test User",
        is_doctor=False,
    )


def test_purpose_column_isolation(monkeypatch):
    """A password_reset code must not be rate-limited by email_verification cooldown."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    # Register creates an email_verification code
    asyncio.run(register(UserRegister(email="iso@test.local", password="password123", full_name="Iso", is_doctor=False), db=db))
    assert len(sent_codes) == 1

    # Request a password_reset code — must NOT be blocked by email_verification cooldown
    asyncio.run(forgot_password(ForgotPasswordRequest(email="iso@test.local"), db=db))
    assert len(sent_codes) == 2

    # Verify: two codes exist with different purposes
    codes = db.query(EmailVerificationCode).filter(EmailVerificationCode.email == "iso@test.local").all()
    purposes = {c.purpose for c in codes}
    assert "email_verification" in purposes
    assert "password_reset" in purposes


def test_forgot_password_unknown_email(monkeypatch):
    """Unknown email must return 200 (no account enumeration)."""
    db = _setup_db()
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: None)
    resp = asyncio.run(forgot_password(ForgotPasswordRequest(email="nobody@test.local"), db=db))
    assert resp.status == "ok"


def _register_and_verify(email: str, password: str, db, sent_codes: list[str]):
    """Helper: register + verify email, return the user."""
    asyncio.run(register(UserRegister(email=email, password=password, full_name="User", is_doctor=False), db=db))
    reg_code = sent_codes[-1]
    asyncio.run(verify_email(VerifyEmailRequest(email=email, code=reg_code), db=db))


def test_full_reset_flow(monkeypatch):
    """Happy path: forgot → verify code → reset password → login with new password."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("reset@test.local", "old-password-1", db, sent_codes)

    # Request password reset
    asyncio.run(forgot_password(ForgotPasswordRequest(email="reset@test.local"), db=db))
    reset_code = sent_codes[-1]

    # Verify the reset code → get reset_token
    token_resp = asyncio.run(verify_reset_code(
        VerifyResetCodeRequest(email="reset@test.local", code=reset_code), db=db
    ))
    assert token_resp.reset_token

    # Reset the password
    status_resp = asyncio.run(reset_password(
        ResetPasswordRequest(reset_token=token_resp.reset_token, new_password="new-password-2"), db=db
    ))
    assert status_resp.status == "ok"

    # Old password must fail
    with pytest.raises(HTTPException) as exc:
        asyncio.run(login(UserLogin(email="reset@test.local", password="old-password-1"), db=db))
    assert exc.value.status_code == 401

    # New password must work
    auth_resp = asyncio.run(login(UserLogin(email="reset@test.local", password="new-password-2"), db=db))
    assert auth_resp.accessToken is not None


def test_reset_code_wrong_code(monkeypatch):
    """Wrong code increments attempts and raises 400."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("wrong@test.local", "password123", db, sent_codes)
    asyncio.run(forgot_password(ForgotPasswordRequest(email="wrong@test.local"), db=db))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_reset_code(
            VerifyResetCodeRequest(email="wrong@test.local", code="000000"), db=db
        ))
    assert exc.value.status_code == 400

    code_row = (
        db.query(EmailVerificationCode)
        .filter(EmailVerificationCode.email == "wrong@test.local",
                EmailVerificationCode.purpose == "password_reset")
        .first()
    )
    assert code_row.attempts == 1


def test_reset_code_expired(monkeypatch):
    """Expired reset code raises 400."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("expired@test.local", "password123", db, sent_codes)
    asyncio.run(forgot_password(ForgotPasswordRequest(email="expired@test.local"), db=db))

    # Manually expire the reset code
    code_row = (
        db.query(EmailVerificationCode)
        .filter(EmailVerificationCode.email == "expired@test.local",
                EmailVerificationCode.purpose == "password_reset")
        .first()
    )
    code_row.expires_at = dt.datetime.utcnow() - dt.timedelta(minutes=1)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_reset_code(
            VerifyResetCodeRequest(email="expired@test.local", code=sent_codes[-1]), db=db
        ))
    assert exc.value.status_code == 400


def test_reset_token_wrong_purpose(monkeypatch):
    """A regular login JWT must be rejected by reset-password endpoint."""
    db = _setup_db()
    from backend.auth import create_access_token
    bad_token = create_access_token(data={"sub": "1"})  # no purpose claim

    with pytest.raises(HTTPException) as exc:
        asyncio.run(reset_password(
            ResetPasswordRequest(reset_token=bad_token, new_password="new-password-x"), db=db
        ))
    assert exc.value.status_code == 400


def test_reset_codes_invalidated_after_reset(monkeypatch):
    """All active reset codes for the user are marked used after a successful reset."""
    db = _setup_db()
    sent_codes: list[str] = []
    monkeypatch.setattr(auth_routes, "send_verification_code_email", lambda e, c: sent_codes.append(c))

    _register_and_verify("cleanup@test.local", "password123", db, sent_codes)
    asyncio.run(forgot_password(ForgotPasswordRequest(email="cleanup@test.local"), db=db))
    reset_code = sent_codes[-1]

    token_resp = asyncio.run(verify_reset_code(
        VerifyResetCodeRequest(email="cleanup@test.local", code=reset_code), db=db
    ))
    asyncio.run(reset_password(
        ResetPasswordRequest(reset_token=token_resp.reset_token, new_password="brand-new-pass"), db=db
    ))

    active_codes = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == "cleanup@test.local",
            EmailVerificationCode.purpose == "password_reset",
            EmailVerificationCode.used_at.is_(None),
        )
        .count()
    )
    assert active_codes == 0
```

- [ ] **Step 2: Run the test — confirm it fails (ForgotPasswordRequest not yet defined)**

```bash
cd backend && python -m pytest tests/test_auth_password_reset.py -v 2>&1 | head -30
```

Expected: `ImportError` — `ForgotPasswordRequest` doesn't exist yet.

- [ ] **Step 3: Add `purpose` parameter to `_create_verification_code()` in `auth_routes.py`**

Replace the entire `_create_verification_code` function body:

```python
def _create_verification_code(db: Session, user: User, purpose: str = "email_verification") -> EmailVerificationCode:
    now = dt.datetime.utcnow()
    one_hour_ago = now - dt.timedelta(hours=1)
    recent_sends = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == user.email,
            EmailVerificationCode.created_at >= one_hour_ago,
            EmailVerificationCode.purpose == purpose,
        )
        .count()
    )
    if recent_sends >= EMAIL_CODE_MAX_SENDS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification emails sent. Please try later.",
        )

    latest_code = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == user.email,
            EmailVerificationCode.used_at.is_(None),
            EmailVerificationCode.purpose == purpose,
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )
    if latest_code:
        cooldown_delta = (now - latest_code.created_at).total_seconds()
        if cooldown_delta < EMAIL_CODE_COOLDOWN_SECONDS:
            wait_for = int(EMAIL_CODE_COOLDOWN_SECONDS - cooldown_delta)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait_for}s before requesting a new code.",
            )
        latest_code.used_at = now

    code = _generate_email_code()
    code_row = EmailVerificationCode(
        user_id=user.id,
        email=user.email,
        code_hash=_hash_email_code(code),
        expires_at=now + dt.timedelta(minutes=EMAIL_CODE_TTL_MINUTES),
        attempts=0,
        purpose=purpose,
    )
    db.add(code_row)
    db.flush()

    try:
        send_verification_code_email(user.email, code)
    except Exception:
        logger.exception("Failed to send verification email to %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send verification email. Please try again.",
        )

    return code_row
```

- [ ] **Step 4: Add Pydantic request/response models to `auth_routes.py`**

Add after the existing `ResendEmailCodeRequest` model:

```python
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        code = value.strip()
        if not code.isdigit() or len(code) != 6:
            raise ValueError("Code must be exactly 6 digits.")
        return code


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(value.encode("utf-8")) > 1024:
            raise ValueError("Password must be at most 1024 bytes.")
        return value


class ResetTokenResponse(BaseModel):
    reset_token: str


class StatusResponse(BaseModel):
    status: str
```

- [ ] **Step 5: Run isolation test — should still fail (forgot_password function not yet defined)**

```bash
cd backend && python -m pytest tests/test_auth_password_reset.py::test_purpose_column_isolation -v
```

Expected: still `ImportError` on `forgot_password`.

- [ ] **Step 6: Commit (from repo root)**

```bash
git add backend/auth_routes.py backend/tests/test_auth_password_reset.py && git commit -m "feat: add purpose param to _create_verification_code and password-reset request models"
```

---

## Task 3: Backend — add 3 password-reset endpoints

**Files:**
- Modify: `backend/auth_routes.py`

- [ ] **Step 1: Add `decode_token` to the import in `auth_routes.py`**

Find the existing import block from `backend.auth` (lines ~14-19) and add `decode_token`:

```python
from backend.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    get_current_user_id,
)
```

- [ ] **Step 2: Run tests — confirm they fail with ImportError**

```bash
cd backend && python -m pytest tests/test_auth_password_reset.py -v 2>&1 | head -20
```

Expected: `ImportError` — `forgot_password` not yet defined.

- [ ] **Step 2: Add the 3 endpoints to `auth_routes.py`**

Add after the `resend_email_code` endpoint:

```python
@router.post("/forgot-password", response_model=StatusResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password-reset code. Always returns 200 to prevent account enumeration."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return StatusResponse(status="ok")
    try:
        _create_verification_code(db, user, purpose="password_reset")
        db.commit()
    except HTTPException as exc:
        db.rollback()
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            return StatusResponse(status="ok")
        raise
    except Exception:
        db.rollback()
        logger.exception("forgot_password failed for email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send reset email. Please try again.",
        )
    return StatusResponse(status="ok")


@router.post("/verify-reset-code", response_model=ResetTokenResponse)
async def verify_reset_code(payload: VerifyResetCodeRequest, db: Session = Depends(get_db)):
    """Verify the password-reset OTP and return a short-lived reset_token JWT."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    code_row = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.used_at.is_(None),
            EmailVerificationCode.purpose == "password_reset",
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )
    if not code_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset code not found. Request a new one.")

    now = dt.datetime.utcnow()
    if code_row.expires_at < now:
        code_row.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset code expired. Request a new one.")

    if code_row.attempts >= EMAIL_CODE_MAX_ATTEMPTS:
        code_row.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    expected_hash = _hash_email_code(payload.code)
    if not hmac.compare_digest(expected_hash, code_row.code_hash):
        code_row.attempts = code_row.attempts + 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset code.")

    code_row.used_at = now
    db.commit()

    reset_token = create_access_token(
        data={"sub": str(user.id), "purpose": "password_reset"},
        expires_delta=dt.timedelta(minutes=15),
    )
    return ResetTokenResponse(reset_token=reset_token)


@router.post("/reset-password", response_model=StatusResponse)
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Set new password using a valid reset_token JWT."""
    try:
        token_payload = decode_token(payload.reset_token)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    if token_payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token.")

    user_id = int(token_payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.hashed_password = get_password_hash(payload.new_password)

    # Invalidate any remaining active reset codes for this user
    now = dt.datetime.utcnow()
    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.user_id == user_id,
        EmailVerificationCode.purpose == "password_reset",
        EmailVerificationCode.used_at.is_(None),
    ).update({"used_at": now})

    db.commit()
    return StatusResponse(status="ok")
```

- [ ] **Step 3: Run all password-reset tests**

```bash
cd backend && python -m pytest tests/test_auth_password_reset.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 4: Run existing auth tests to confirm no regressions**

```bash
cd backend && python -m pytest tests/test_auth_email_verification.py -v
```

Expected: all existing tests PASS.

- [ ] **Step 5: Commit (from repo root)**

```bash
git add backend/auth_routes.py && git commit -m "feat: add forgot-password, verify-reset-code, reset-password endpoints"
```

---

## Task 4: Frontend — i18n keys

**Files:**
- Modify: `frontend/src/assets/i18n/es.json`
- Modify: `frontend/src/assets/i18n/en.json`
- Modify: `frontend/src/assets/i18n/ru.json`

- [ ] **Step 1: Add keys to `es.json`**

In the `"AUTH"` object, add after `"EMAIL_CODE_PLACEHOLDER": "123456"`:

```json
"FORGOT_LINK": "¿Olvidaste tu contraseña?",
"WELCOME_FORGOT": "Ingresa tu correo para recibir un código de restablecimiento.",
"WELCOME_RESET_VERIFY": "Ingresa el código que enviamos a tu correo.",
"WELCOME_RESET_PASSWORD": "Crea tu nueva contraseña.",
"FORGOT_BUTTON": "Enviar código",
"FORGOT_SENDING": "Enviando...",
"RESET_VERIFY_BUTTON": "Verificar código",
"RESET_VERIFYING": "Verificando...",
"RESET_PASSWORD_NEW": "Nueva contraseña",
"RESET_PASSWORD_CONFIRM": "Confirmar nueva contraseña",
"RESET_PASSWORD_BUTTON": "Guardar contraseña",
"RESET_PASSWORD_SAVING": "Guardando...",
"RESET_CODE_SENT": "Código enviado a {{email}}.",
"RESET_PASSWORD_SUCCESS": "Contraseña actualizada. Inicia sesión."
```

In the `"ERRORS"` object, add after `"AUTH_RESEND_FAILED"`:

```json
"AUTH_FORGOT_FAILED": "No se pudo enviar el código. Intenta de nuevo.",
"AUTH_RESET_VERIFY_FAILED": "Código incorrecto o expirado. Intenta de nuevo.",
"AUTH_RESET_PASSWORD_FAILED": "No se pudo restablecer la contraseña. Intenta de nuevo.",
"RESET_PASSWORD_MISMATCH": "Las contraseñas deben coincidir."
```

- [ ] **Step 2: Add keys to `en.json`**

In `"AUTH"` object, add after `"EMAIL_CODE_PLACEHOLDER": "123456"`:

```json
"FORGOT_LINK": "Forgot your password?",
"WELCOME_FORGOT": "Enter your email to receive a password-reset code.",
"WELCOME_RESET_VERIFY": "Enter the code we sent to your email.",
"WELCOME_RESET_PASSWORD": "Create your new password.",
"FORGOT_BUTTON": "Send code",
"FORGOT_SENDING": "Sending...",
"RESET_VERIFY_BUTTON": "Verify code",
"RESET_VERIFYING": "Verifying...",
"RESET_PASSWORD_NEW": "New password",
"RESET_PASSWORD_CONFIRM": "Confirm new password",
"RESET_PASSWORD_BUTTON": "Save password",
"RESET_PASSWORD_SAVING": "Saving...",
"RESET_CODE_SENT": "Code sent to {{email}}.",
"RESET_PASSWORD_SUCCESS": "Password updated. Sign in."
```

In `"ERRORS"` object, add after `"AUTH_RESEND_FAILED"`:

```json
"AUTH_FORGOT_FAILED": "Failed to send code. Please try again.",
"AUTH_RESET_VERIFY_FAILED": "Invalid or expired code. Please try again.",
"AUTH_RESET_PASSWORD_FAILED": "Failed to reset password. Please try again.",
"RESET_PASSWORD_MISMATCH": "Passwords must match."
```

- [ ] **Step 3: Add keys to `ru.json`**

In `"AUTH"` object, add after `"EMAIL_CODE_PLACEHOLDER": "123456"`:

```json
"FORGOT_LINK": "Забыли пароль?",
"WELCOME_FORGOT": "Введите email, чтобы получить код сброса пароля.",
"WELCOME_RESET_VERIFY": "Введите код, который мы отправили на вашу почту.",
"WELCOME_RESET_PASSWORD": "Создайте новый пароль.",
"FORGOT_BUTTON": "Отправить код",
"FORGOT_SENDING": "Отправка...",
"RESET_VERIFY_BUTTON": "Проверить код",
"RESET_VERIFYING": "Проверяем...",
"RESET_PASSWORD_NEW": "Новый пароль",
"RESET_PASSWORD_CONFIRM": "Подтвердить новый пароль",
"RESET_PASSWORD_BUTTON": "Сохранить пароль",
"RESET_PASSWORD_SAVING": "Сохраняем...",
"RESET_CODE_SENT": "Код отправлен на {{email}}.",
"RESET_PASSWORD_SUCCESS": "Пароль обновлён. Войдите снова."
```

In `"ERRORS"` object, add after `"AUTH_RESEND_FAILED"`:

```json
"AUTH_FORGOT_FAILED": "Не удалось отправить код. Попробуйте ещё раз.",
"AUTH_RESET_VERIFY_FAILED": "Неверный или истёкший код. Попробуйте ещё раз.",
"AUTH_RESET_PASSWORD_FAILED": "Не удалось сбросить пароль. Попробуйте ещё раз.",
"RESET_PASSWORD_MISMATCH": "Пароли должны совпадать."
```

- [ ] **Step 4: Commit (from repo root)**

```bash
git add frontend/src/assets/i18n/ && git commit -m "feat: add password-reset i18n keys (es/en/ru)"
```

---

## Task 5: Frontend — `AuthService` additions

**Files:**
- Modify: `frontend/src/app/core/services/auth.service.ts`

- [ ] **Step 1: Add 3 methods to `AuthService`**

Add after `resendEmailCode()`:

```typescript
forgotPassword(payload: { email: string }): Observable<{ status: string }> {
  return this.api.post<{ status: string }>('/auth/forgot-password', payload);
}

verifyResetCode(payload: { email: string; code: string }): Observable<{ reset_token: string }> {
  return this.api.post<{ reset_token: string }>('/auth/verify-reset-code', payload);
}

resetPassword(payload: { reset_token: string; new_password: string }): Observable<{ status: string }> {
  return this.api.post<{ status: string }>('/auth/reset-password', payload);
}
```

- [ ] **Step 2: Commit (from repo root)**

```bash
git add frontend/src/app/core/services/auth.service.ts && git commit -m "feat: add forgotPassword, verifyResetCode, resetPassword to AuthService"
```

---

## Task 6: Frontend — component logic

**Files:**
- Modify: `frontend/src/app/features/auth/pages/auth-page/auth-page.component.ts`

- [ ] **Step 1: Extend mode type and add state fields**

Change:
```typescript
mode: 'login' | 'register' | 'verify' = 'login';
```
To:
```typescript
mode: 'login' | 'register' | 'verify' | 'forgot' | 'reset-verify' | 'reset-password' = 'login';
```

Add after `pendingVerificationEmail = ''`:
```typescript
pendingResetEmail = '';
resetToken = '';
```

- [ ] **Step 2: Add new forms**

Add after `verifyForm`:

```typescript
readonly forgotForm = this.fb.nonNullable.group({
  email: ['', [Validators.required, Validators.email]],
});

readonly resetPasswordForm = this.fb.nonNullable.group({
  password: ['', [Validators.required, Validators.minLength(8)]],
  confirmPassword: ['', [Validators.required]],
});
```

- [ ] **Step 3: Add navigation + submit methods**

Add after `resendCode()`:

```typescript
goToForgot(): void {
  this.mode = 'forgot';
  this.errorMessage = '';
  this.infoMessage = '';
  this.forgotForm.reset();
}

backToLogin(): void {
  this.mode = 'login';
  this.errorMessage = '';
  this.infoMessage = '';
  this.pendingResetEmail = '';
  this.resetToken = '';
  this.forgotForm.reset();
  this.verifyForm.reset();
  this.resetPasswordForm.reset();
}

submitForgot(): void {
  if (this.forgotForm.invalid) {
    this.forgotForm.markAllAsTouched();
    return;
  }
  this.isSubmitting = true;
  this.errorMessage = '';
  this.infoMessage = '';
  const { email } = this.forgotForm.getRawValue();
  this.auth.forgotPassword({ email }).subscribe({
    next: () => {
      this.pendingResetEmail = email;
      this.mode = 'reset-verify';
      this.verifyForm.reset();
      this.infoMessage = this.translate.instant('AUTH.RESET_CODE_SENT', { email });
    },
    error: (err) => {
      this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_FORGOT_FAILED');
      this.isSubmitting = false;
    },
    complete: () => (this.isSubmitting = false),
  });
}

submitResetVerify(): void {
  if (this.verifyForm.invalid || !this.pendingResetEmail) {
    this.verifyForm.markAllAsTouched();
    return;
  }
  this.isSubmitting = true;
  this.errorMessage = '';
  this.infoMessage = '';
  const { code } = this.verifyForm.getRawValue();
  this.auth.verifyResetCode({ email: this.pendingResetEmail, code }).subscribe({
    next: (resp) => {
      this.resetToken = resp.reset_token;
      this.mode = 'reset-password';
      this.resetPasswordForm.reset();
    },
    error: (err) => {
      this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_RESET_VERIFY_FAILED');
      this.isSubmitting = false;
    },
    complete: () => (this.isSubmitting = false),
  });
}

resendResetCode(): void {
  if (!this.pendingResetEmail || this.isSubmitting) return;
  this.isSubmitting = true;
  this.errorMessage = '';
  this.infoMessage = '';
  this.auth.forgotPassword({ email: this.pendingResetEmail }).subscribe({
    next: () => {
      this.infoMessage = this.translate.instant('AUTH.RESET_CODE_SENT', { email: this.pendingResetEmail });
    },
    error: (err) => {
      this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_FORGOT_FAILED');
    },
    complete: () => (this.isSubmitting = false),
  });
}

submitResetPassword(): void {
  if (this.resetPasswordForm.invalid || !this.resetToken) {
    this.resetPasswordForm.markAllAsTouched();
    return;
  }
  const { password, confirmPassword } = this.resetPasswordForm.getRawValue();
  if (password !== confirmPassword) {
    this.errorMessage = this.translate.instant('ERRORS.RESET_PASSWORD_MISMATCH');
    return;
  }
  this.isSubmitting = true;
  this.errorMessage = '';
  this.infoMessage = '';
  this.auth.resetPassword({ reset_token: this.resetToken, new_password: password }).subscribe({
    next: () => {
      this.pendingResetEmail = '';
      this.resetToken = '';
      this.mode = 'login';
      this.infoMessage = this.translate.instant('AUTH.RESET_PASSWORD_SUCCESS');
    },
    error: (err) => {
      this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_RESET_PASSWORD_FAILED');
      this.isSubmitting = false;
    },
    complete: () => (this.isSubmitting = false),
  });
}
```

- [ ] **Step 4: Commit (from repo root)**

```bash
git add frontend/src/app/features/auth/pages/auth-page/auth-page.component.ts && git commit -m "feat: add password-reset logic to auth-page component"
```

---

## Task 7: Frontend — HTML template

**Files:**
- Modify: `frontend/src/app/features/auth/pages/auth-page/auth-page.component.html`

- [ ] **Step 1: Update subtitle `<p>` to cover new modes**

Replace the subtitle `<p>` element:

```html
<p class="text-sm text-[var(--text-dim)]">
  {{
    mode === 'login'
      ? ('AUTH.WELCOME_LOGIN' | translate)
      : mode === 'register'
        ? ('AUTH.WELCOME_REGISTER' | translate)
        : mode === 'verify'
          ? ('AUTH.WELCOME_VERIFY' | translate)
          : mode === 'forgot'
            ? ('AUTH.WELCOME_FORGOT' | translate)
            : mode === 'reset-verify'
              ? ('AUTH.WELCOME_RESET_VERIFY' | translate)
              : ('AUTH.WELCOME_RESET_PASSWORD' | translate)
  }}
</p>
```

- [ ] **Step 2: Replace header buttons**

Replace the two existing header `<button>` elements with:

```html
<!-- Back to login — shown on verify, forgot, reset-verify, reset-password -->
<button
  type="button"
  appGlassButton
  (click)="backToLogin()"
  *ngIf="mode === 'verify' || mode === 'forgot' || mode === 'reset-verify' || mode === 'reset-password'">
  <span class="material-symbols-rounded">login</span>
  <span>{{ 'AUTH.SWITCH_TO_LOGIN' | translate }}</span>
</button>

<!-- Toggle login/register — only on login and register -->
<button
  type="button"
  appGlassButton
  (click)="toggleMode()"
  *ngIf="mode === 'login' || mode === 'register'">
  <span class="material-symbols-rounded">{{ mode === 'login' ? 'person_add' : 'login' }}</span>
  <span>{{ mode === 'login' ? ('AUTH.SWITCH_TO_REGISTER' | translate) : ('AUTH.SWITCH_TO_LOGIN' | translate) }}</span>
</button>
```

Note: `backToLogin()` now handles the `verify` mode back button too (it resets `verifyForm` and `pendingVerificationEmail`). Update `toggleMode()` to also reset `pendingVerificationEmail` — verify that `toggleMode()` in the component already clears it (it does: `this.pendingVerificationEmail = ''`). No extra change needed.

- [ ] **Step 3: Add "forgot password" link + success toast to login form**

Inside `<form *ngIf="mode === 'login'"`, add after the password `app-glass-input` and before the error toast:

```html
<div class="flex justify-end">
  <button
    type="button"
    class="text-xs text-[var(--text-dim)] hover:text-[var(--text)] underline underline-offset-2 transition-colors"
    (click)="goToForgot()">
    {{ 'AUTH.FORGOT_LINK' | translate }}
  </button>
</div>
```

Add after the error toast `*ngIf="errorMessage"` in the login form:

```html
<div *ngIf="infoMessage" class="toast-glass success" role="status">
  <span class="material-symbols-rounded">check_circle</span>
  <span>{{ infoMessage }}</span>
</div>
```

- [ ] **Step 4: Add `forgot` form section**

Add after the closing `</form>` of the `register` form:

```html
<form *ngIf="mode === 'forgot'" [formGroup]="forgotForm" (ngSubmit)="submitForgot()" class="space-y-5">
  <app-glass-input
    [label]="'AUTH.EMAIL' | translate"
    [placeholder]="'AUTH.EMAIL_PLACEHOLDER' | translate"
    type="email"
    formControlName="email">
  </app-glass-input>

  <div *ngIf="errorMessage" class="toast-glass error" role="alert">
    <span class="material-symbols-rounded">error</span>
    <span>{{ errorMessage }}</span>
  </div>

  <button type="submit" appGlassButton [glassBlock]="true" [disabled]="isSubmitting">
    <span *ngIf="isSubmitting" class="loader-dot"></span>
    <span>{{ isSubmitting ? ('AUTH.FORGOT_SENDING' | translate) : ('AUTH.FORGOT_BUTTON' | translate) }}</span>
  </button>
</form>
```

- [ ] **Step 5: Add `reset-verify` form section**

Add after the `forgot` form:

```html
<form *ngIf="mode === 'reset-verify'" [formGroup]="verifyForm" (ngSubmit)="submitResetVerify()" class="space-y-5">
  <div class="flex flex-col gap-2">
    <label class="text-xs uppercase tracking-[0.2em] text-[var(--text-dim)]">{{ 'AUTH.EMAIL' | translate }}</label>
    <div class="input-glass">{{ pendingResetEmail }}</div>
  </div>

  <div class="flex flex-col gap-3">
    <label class="text-xs uppercase tracking-[0.2em] text-[var(--text-dim)]">{{ 'AUTH.EMAIL_CODE' | translate }}</label>
    <app-otp-input formControlName="code"></app-otp-input>
  </div>

  <div *ngIf="infoMessage" class="toast-glass success" role="status">
    <span class="material-symbols-rounded">info</span>
    <span>{{ infoMessage }}</span>
  </div>

  <div *ngIf="errorMessage" class="toast-glass error" role="alert">
    <span class="material-symbols-rounded">error</span>
    <span>{{ errorMessage }}</span>
  </div>

  <button type="submit" appGlassButton [glassBlock]="true" [disabled]="isSubmitting">
    <span *ngIf="isSubmitting" class="loader-dot"></span>
    <span>{{ isSubmitting ? ('AUTH.RESET_VERIFYING' | translate) : ('AUTH.RESET_VERIFY_BUTTON' | translate) }}</span>
  </button>

  <button type="button" appGlassButton [glassBlock]="true" [disabled]="isSubmitting" (click)="resendResetCode()">
    <span>{{ 'AUTH.RESEND_CODE' | translate }}</span>
  </button>
</form>
```

- [ ] **Step 6: Add `reset-password` form section**

Add after the `reset-verify` form:

```html
<form *ngIf="mode === 'reset-password'" [formGroup]="resetPasswordForm" (ngSubmit)="submitResetPassword()" class="space-y-5">
  <app-glass-input
    [label]="'AUTH.RESET_PASSWORD_NEW' | translate"
    [placeholder]="'AUTH.PASSWORD_MIN_PLACEHOLDER' | translate"
    type="password"
    formControlName="password">
  </app-glass-input>
  <app-glass-input
    [label]="'AUTH.RESET_PASSWORD_CONFIRM' | translate"
    [placeholder]="'AUTH.CONFIRM_PASSWORD_PLACEHOLDER' | translate"
    type="password"
    formControlName="confirmPassword">
  </app-glass-input>

  <div *ngIf="errorMessage" class="toast-glass error" role="alert">
    <span class="material-symbols-rounded">error</span>
    <span>{{ errorMessage }}</span>
  </div>

  <button type="submit" appGlassButton [glassBlock]="true" [disabled]="isSubmitting">
    <span *ngIf="isSubmitting" class="loader-dot"></span>
    <span>{{ isSubmitting ? ('AUTH.RESET_PASSWORD_SAVING' | translate) : ('AUTH.RESET_PASSWORD_BUTTON' | translate) }}</span>
  </button>
</form>
```

- [ ] **Step 7: Commit (from repo root)**

```bash
git add frontend/src/app/features/auth/pages/auth-page/auth-page.component.html && git commit -m "feat: add password-reset UI to auth-page template"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Build frontend**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 3: Manual smoke test (dev server)**

Start backend:
```bash
cd backend && uvicorn main:app --reload --port 8000
```

Start frontend (separate terminal):
```bash
cd frontend && npm start
```

Test the flow:
1. Open login page → click "¿Olvidaste tu contraseña?"
2. Enter a registered email → click "Enviar código"
3. Check backend logs for the 6-digit code (SMTP not configured in dev → logged to console)
4. Enter the code → click "Verificar código"
5. Enter new password + confirm → click "Guardar contraseña"
6. Confirm redirect to login with success message "Contraseña actualizada. Inicia sesión."
7. Sign in with the new password — should succeed
8. Sign in with the old password — should fail with 401

- [ ] **Step 4: Commit any fixes found during smoke test**

```bash
git add -A && git commit -m "fix: address issues found during smoke test"
```
