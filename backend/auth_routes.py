"""Authentication routes."""

import datetime as dt
import hashlib
import hmac
import logging
import os
import random
import re
import secrets
from functools import lru_cache

import jwt
import requests
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Literal, Optional
from backend.database import AuditLog, EmailVerificationCode, OAuthIdentity, User, SessionLocal
from backend.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    get_current_user_id,
)
from backend.admin_auth import is_admin_email
from backend.email_service import send_verification_code_email

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


EMAIL_CODE_TTL_MINUTES = _env_int("EMAIL_CODE_TTL_MINUTES", 10)
EMAIL_CODE_MAX_ATTEMPTS = _env_int("EMAIL_CODE_MAX_ATTEMPTS", 5)
EMAIL_CODE_COOLDOWN_SECONDS = _env_int("EMAIL_CODE_COOLDOWN_SECONDS", 60)
EMAIL_CODE_MAX_SENDS_PER_HOUR = _env_int("EMAIL_CODE_MAX_SENDS_PER_HOUR", 6)
EMAIL_CODE_SALT = os.getenv("EMAIL_CODE_SALT", "dev-email-code-salt")


# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_doctor: bool = False

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        # Keep a sane upper bound to avoid abuse.
        if len(value.encode("utf-8")) > 1024:
            raise ValueError("Password must be at most 1024 bytes.")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 1024:
            raise ValueError("Password must be at most 1024 bytes.")
        return value


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    accessToken: str  # camelCase for frontend
    user: "UserResponse"


class SocialAuthResponse(AuthResponse):
    isNewUser: bool = False


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_doctor: bool = False
    is_active: bool = True
    email_verified: bool = False
    role: str = "PATIENT"  # Added for frontend compatibility


class RegisterResponse(BaseModel):
    status: str = "verification_required"
    email: str
    message: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        code = value.strip()
        if not code.isdigit() or len(code) != 6:
            raise ValueError("Code must be exactly 6 digits.")
        return code


class ResendEmailCodeRequest(BaseModel):
    email: EmailStr


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


class SocialProviderConfig(BaseModel):
    googleClientId: str | None = None
    facebookAppId: str | None = None
    facebookApiVersion: str = "v25.0"


class SocialAuthRequest(BaseModel):
    provider: Literal["google", "facebook"]
    credential: str = Field(min_length=20, max_length=8192)
    action: Literal["login", "register"] = "login"
    is_doctor: bool = False


class SocialProfile(BaseModel):
    provider: Literal["google", "facebook"]
    subject: str = Field(min_length=1, max_length=255)
    email: EmailStr
    full_name: str | None = None


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _audit_auth_event(
    db: Session,
    *,
    action: str,
    email: str,
    status_value: str,
    user: User | None = None,
    metadata: dict | None = None,
) -> None:
    """Record auth audit events without storing passwords, OTPs, or tokens."""
    db.add(
        AuditLog(
            actor_user_id=user.id if user else None,
            actor_role="doctor" if user and user.is_doctor else ("patient" if user else None),
            action=action,
            resource_type="auth",
            resource_id=str(user.id) if user else None,
            status=status_value,
            metadata_json={"email": email.lower(), **(metadata or {})},
        )
    )


def _hash_email_code(code: str) -> str:
    digest = hashlib.sha256(f"{EMAIL_CODE_SALT}:{code}".encode("utf-8")).hexdigest()
    return digest


def _generate_email_code() -> str:
    generator = random.SystemRandom()
    return f"{generator.randint(0, 999999):06d}"


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
        send_verification_code_email(user.email, code, purpose=purpose)
    except Exception:
        logger.exception("Failed to send verification email to %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send verification email. Please try again.",
        )

    return code_row


def _ensure_email_verification_code(db: Session, user: User) -> bool:
    """Keep a usable verification code available, sending a new one only when needed."""
    now = dt.datetime.utcnow()
    latest_code = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.used_at.is_(None),
            EmailVerificationCode.purpose == "email_verification",
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )
    if (
        latest_code
        and latest_code.expires_at >= now
        and latest_code.attempts < EMAIL_CODE_MAX_ATTEMPTS
    ):
        return False

    _create_verification_code(db, user)
    return True


def _build_user_response(user: User) -> UserResponse:
    role = "ADMIN" if is_admin_email(user.email) else ("DOCTOR" if user.is_doctor else "PATIENT")
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_doctor=user.is_doctor,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
        role=role,
    )


def _social_error(
    status_code: int,
    code: str,
    message: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _google_client_id() -> str | None:
    return (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip() or None


def _facebook_app_id() -> str | None:
    return (os.getenv("FACEBOOK_APP_ID") or "").strip() or None


def _facebook_app_secret() -> str | None:
    return (os.getenv("FACEBOOK_APP_SECRET") or "").strip() or None


def _facebook_api_version() -> str:
    configured = (os.getenv("FACEBOOK_API_VERSION") or "v25.0").strip()
    return configured if re.fullmatch(r"v\d+\.\d+", configured) else "v25.0"


@lru_cache(maxsize=1)
def _google_jwk_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        "https://www.googleapis.com/oauth2/v3/certs",
        cache_jwk_set=True,
        lifespan=3600,
    )


def _verify_google_credential(credential: str) -> SocialProfile:
    client_id = _google_client_id()
    if not client_id:
        raise _social_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "social_provider_unavailable",
            "El acceso con Google no está configurado.",
        )

    try:
        signing_key = _google_jwk_client().get_signing_key_from_jwt(credential).key
        claims = jwt.decode(
            credential,
            signing_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=["accounts.google.com", "https://accounts.google.com"],
            options={"require": ["aud", "email", "exp", "iat", "iss", "sub"]},
        )
        email_verified = claims.get("email_verified")
        if email_verified not in (True, "true"):
            raise ValueError("Google email is not verified")
        return SocialProfile(
            provider="google",
            subject=str(claims["sub"]),
            email=claims["email"],
            full_name=(claims.get("name") or "").strip() or None,
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, ValidationError):
        raise _social_error(
            status.HTTP_401_UNAUTHORIZED,
            "social_credential_invalid",
            "No se pudo validar tu cuenta de Google. Inténtalo de nuevo.",
        )


def _facebook_graph_get(
    path: str,
    *,
    access_token: str,
    params: dict[str, str] | None = None,
) -> dict:
    response = requests.get(
        f"https://graph.facebook.com/{_facebook_api_version()}/{path}",
        params=params,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected Facebook response")
    return payload


def _verify_facebook_credential(credential: str) -> SocialProfile:
    app_id = _facebook_app_id()
    app_secret = _facebook_app_secret()
    if not app_id or not app_secret:
        raise _social_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "social_provider_unavailable",
            "El acceso con Facebook no está configurado.",
        )

    try:
        app_access_token = f"{app_id}|{app_secret}"
        debug_payload = _facebook_graph_get(
            "debug_token",
            access_token=app_access_token,
            params={"input_token": credential},
        )
        token_data = debug_payload.get("data")
        if (
            not isinstance(token_data, dict)
            or token_data.get("is_valid") is not True
            or str(token_data.get("app_id")) != app_id
            or not token_data.get("user_id")
        ):
            raise ValueError("Invalid Facebook access token")

        app_secret_proof = hmac.new(
            app_secret.encode("utf-8"),
            credential.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        profile_payload = _facebook_graph_get(
            "me",
            access_token=credential,
            params={
                "fields": "id,name,email",
                "appsecret_proof": app_secret_proof,
            },
        )
        if str(profile_payload.get("id")) != str(token_data["user_id"]):
            raise ValueError("Facebook user mismatch")
        if not profile_payload.get("email"):
            raise _social_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "social_email_unavailable",
                "Facebook no compartió tu correo. Autoriza el permiso de correo e inténtalo de nuevo.",
            )
        return SocialProfile(
            provider="facebook",
            subject=str(profile_payload["id"]),
            email=profile_payload["email"],
            full_name=(profile_payload.get("name") or "").strip() or None,
        )
    except HTTPException:
        raise
    except (requests.RequestException, KeyError, TypeError, ValueError, ValidationError):
        raise _social_error(
            status.HTTP_401_UNAUTHORIZED,
            "social_credential_invalid",
            "No se pudo validar tu cuenta de Facebook. Inténtalo de nuevo.",
        )


def _verify_social_credential(provider: str, credential: str) -> SocialProfile:
    if provider == "google":
        return _verify_google_credential(credential)
    if provider == "facebook":
        return _verify_facebook_credential(credential)
    raise _social_error(
        status.HTTP_400_BAD_REQUEST,
        "social_provider_invalid",
        "Proveedor de acceso no compatible.",
    )


def _social_auth_response(user: User, *, is_new_user: bool) -> SocialAuthResponse:
    return SocialAuthResponse(
        accessToken=create_access_token(data={"sub": user.id}),
        user=_build_user_response(user),
        isNewUser=is_new_user,
    )


@router.get("/social/config", response_model=SocialProviderConfig)
async def social_provider_config():
    """Expose only public provider identifiers required by the browser SDKs."""
    return SocialProviderConfig(
        googleClientId=_google_client_id(),
        facebookAppId=_facebook_app_id() if _facebook_app_secret() else None,
        facebookApiVersion=_facebook_api_version(),
    )


@router.post("/social", response_model=SocialAuthResponse)
async def social_auth(payload: SocialAuthRequest, db: Session = Depends(get_db)):
    """Verify a provider credential, then create or restore a NephroAI session."""
    profile = _verify_social_credential(payload.provider, payload.credential)
    normalized_email = str(profile.email).strip().lower()
    identity = (
        db.query(OAuthIdentity)
        .filter(
            OAuthIdentity.provider == profile.provider,
            OAuthIdentity.provider_subject == profile.subject,
        )
        .first()
    )

    if identity:
        user = identity.user
        if not user or not user.is_active:
            _audit_auth_event(
                db,
                action="auth_social_login_failed",
                email=normalized_email,
                status_value="failure",
                user=user,
                metadata={"provider": profile.provider, "reason": "inactive"},
            )
            db.commit()
            raise _social_error(
                status.HTTP_403_FORBIDDEN,
                "social_account_inactive",
                "Esta cuenta está desactivada.",
            )
        _audit_auth_event(
            db,
            action="auth_social_login_success",
            email=user.email,
            status_value="success",
            user=user,
            metadata={"provider": profile.provider},
        )
        db.commit()
        return _social_auth_response(user, is_new_user=False)

    existing_user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if existing_user and existing_user.email_verified_at is not None:
        _audit_auth_event(
            db,
            action="auth_social_register_failed",
            email=normalized_email,
            status_value="failure",
            user=existing_user,
            metadata={"provider": profile.provider, "reason": "email_exists"},
        )
        db.commit()
        raise _social_error(
            status.HTTP_409_CONFLICT,
            "social_email_exists",
            "Este correo ya está registrado. Inicia sesión con tu contraseña.",
        )

    if payload.action == "login" and not existing_user:
        _audit_auth_event(
            db,
            action="auth_social_login_failed",
            email=normalized_email,
            status_value="failure",
            metadata={"provider": profile.provider, "reason": "not_found"},
        )
        db.commit()
        raise _social_error(
            status.HTTP_404_NOT_FOUND,
            "social_account_not_found",
            "No existe una cuenta con este acceso. Regístrate primero.",
        )

    is_new_user = existing_user is None
    is_first_activation = is_new_user or existing_user.email_verified_at is None
    user = existing_user or User(
        email=normalized_email,
        hashed_password=get_password_hash(secrets.token_urlsafe(48)),
        full_name=profile.full_name or normalized_email.split("@")[0],
        is_doctor=payload.is_doctor,
        is_active=True,
        email_verified_at=dt.datetime.utcnow(),
    )
    if existing_user:
        user.email = normalized_email
        user.is_active = True
        user.email_verified_at = dt.datetime.utcnow()
        user.is_doctor = payload.is_doctor
        if not user.full_name and profile.full_name:
            user.full_name = profile.full_name

    try:
        if is_new_user:
            db.add(user)
            db.flush()
        db.add(
            OAuthIdentity(
                user_id=user.id,
                provider=profile.provider,
                provider_subject=profile.subject,
            )
        )
        _audit_auth_event(
            db,
            action="auth_social_register_success",
            email=user.email,
            status_value="success",
            user=user,
            metadata={"provider": profile.provider, "new_user": is_new_user},
        )
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception(
            "Social authentication persistence failed provider=%s email=%s",
            profile.provider,
            normalized_email,
        )
        raise _social_error(
            status.HTTP_409_CONFLICT,
            "social_account_conflict",
            "No se pudo completar el acceso. Inténtalo de nuevo.",
        )

    return _social_auth_response(user, is_new_user=is_first_activation)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user and send email verification code."""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        if existing_user.email_verified_at is None:
            try:
                code_sent = _ensure_email_verification_code(db, existing_user)
                _audit_auth_event(
                    db,
                    action="auth_register_resumed",
                    email=existing_user.email,
                    status_value="success",
                    user=existing_user,
                    metadata={"new_code_sent": code_sent},
                )
                db.commit()
            except HTTPException:
                db.rollback()
                raise
            except Exception:
                db.rollback()
                logger.exception("Registration recovery failed for email=%s", user_data.email)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo reanudar la verificación. Inténtalo de nuevo.",
                )
            return RegisterResponse(
                email=existing_user.email,
                message="Verification code available.",
            )

        _audit_auth_event(
            db,
            action="auth_register_failed",
            email=user_data.email,
            status_value="failure",
            user=existing_user,
            metadata={"reason": "email_exists"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este correo ya está registrado. Inicia sesión."
        )

    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name or user_data.email.split("@")[0],
        is_doctor=user_data.is_doctor,
        is_active=False,
        email_verified_at=None,
    )

    try:
        db.add(db_user)
        db.flush()
        _create_verification_code(db, db_user)
        _audit_auth_event(
            db,
            action="auth_register_started",
            email=db_user.email,
            status_value="success",
            user=db_user,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Registration failed for email=%s", user_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )

    return RegisterResponse(
        email=db_user.email,
        message="Verification code sent to email.",
    )


@router.post("/login", response_model=AuthResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user."""
    # Find user
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        _audit_auth_event(
            db,
            action="auth_login_failed",
            email=user_data.email,
            status_value="failure",
            metadata={"reason": "not_found"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos."
        )
    
    # Verify password
    if not verify_password(user_data.password, user.hashed_password):
        _audit_auth_event(
            db,
            action="auth_login_failed",
            email=user.email,
            status_value="failure",
            user=user,
            metadata={"reason": "bad_password"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos."
        )
    
    # Check if active
    if user.email_verified_at is None:
        try:
            code_sent = _ensure_email_verification_code(db, user)
            _audit_auth_event(
                db,
                action="auth_email_verification_resumed",
                email=user.email,
                status_value="success",
                user=user,
                metadata={"new_code_sent": code_sent, "source": "login"},
            )
            db.commit()
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("Login verification recovery failed for email=%s", user.email)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo enviar el código de verificación. Inténtalo de nuevo.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Tu correo aún no está verificado. Ingresa el código que te enviamos.",
                "email": user.email,
            },
        )

    if not user.is_active:
        _audit_auth_event(
            db,
            action="auth_login_failed",
            email=user.email,
            status_value="failure",
            user=user,
            metadata={"reason": "inactive"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta está desactivada.",
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    _audit_auth_event(
        db,
        action="auth_login_success",
        email=user.email,
        status_value="success",
        user=user,
    )
    db.commit()
    
    # Return user + token for frontend
    return AuthResponse(
        accessToken=access_token,
        user=_build_user_response(user)
    )


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with one-time code and activate account."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.email_verified_at is not None and user.is_active:
        access_token = create_access_token(data={"sub": user.id})
        _audit_auth_event(
            db,
            action="auth_email_verify_success",
            email=user.email,
            status_value="success",
            user=user,
            metadata={"already_verified": True},
        )
        db.commit()
        return AuthResponse(accessToken=access_token, user=_build_user_response(user))

    code_row = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.used_at.is_(None),
            EmailVerificationCode.purpose == "email_verification",
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )
    if not code_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code not found. Request a new one.")

    now = dt.datetime.utcnow()
    if code_row.expires_at < now:
        code_row.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code expired. Request a new one.")

    if code_row.attempts >= EMAIL_CODE_MAX_ATTEMPTS:
        code_row.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    expected_hash = _hash_email_code(payload.code)
    if not hmac.compare_digest(expected_hash, code_row.code_hash):
        code_row.attempts = code_row.attempts + 1
        _audit_auth_event(
            db,
            action="auth_email_verify_failed",
            email=user.email,
            status_value="failure",
            user=user,
            metadata={"reason": "bad_code", "attempts": code_row.attempts},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    user.email_verified_at = now
    user.is_active = True
    code_row.used_at = now
    _audit_auth_event(
        db,
        action="auth_email_verify_success",
        email=user.email,
        status_value="success",
        user=user,
    )
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": user.id})
    return AuthResponse(
        accessToken=access_token,
        user=_build_user_response(user),
    )


@router.post("/resend-email-code", response_model=RegisterResponse)
async def resend_email_code(payload: ResendEmailCodeRequest, db: Session = Depends(get_db)):
    """Resend email verification code for non-verified users."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.email_verified_at is not None and user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified.")

    try:
        _create_verification_code(db, user)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to resend verification code email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification code.",
        )

    return RegisterResponse(
        email=user.email,
        message="Verification code sent to email.",
    )


@router.post("/forgot-password", response_model=StatusResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password-reset code. Always returns 200 to prevent account enumeration."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        _audit_auth_event(
            db,
            action="auth_password_reset_requested",
            email=payload.email,
            status_value="success",
            metadata={"account_exists": False},
        )
        db.commit()
        return StatusResponse(status="ok")
    try:
        _create_verification_code(db, user, purpose="password_reset")
        _audit_auth_event(
            db,
            action="auth_password_reset_requested",
            email=user.email,
            status_value="success",
            user=user,
            metadata={"account_exists": True},
        )
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
        _audit_auth_event(
            db,
            action="auth_password_reset_verify_failed",
            email=user.email,
            status_value="failure",
            user=user,
            metadata={"reason": "bad_code", "attempts": code_row.attempts},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset code.")

    code_row.used_at = now
    _audit_auth_event(
        db,
        action="auth_password_reset_verify_success",
        email=user.email,
        status_value="success",
        user=user,
    )
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

    now = dt.datetime.utcnow()
    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.user_id == user_id,
        EmailVerificationCode.purpose == "password_reset",
        EmailVerificationCode.used_at.is_(None),
    ).update({"used_at": now})

    _audit_auth_event(
        db,
        action="auth_password_reset_completed",
        email=user.email,
        status_value="success",
        user=user,
    )
    db.commit()
    return StatusResponse(status="ok")


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current user info."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return _build_user_response(user)


@router.post("/upgrade/doctor", response_model=UserResponse)
async def upgrade_to_doctor(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Mark current user as doctor. Only available in non-production environments."""
    _env = (os.getenv("ENV") or os.getenv("APP_ENV") or "development").lower()
    if _env in {"prod", "production"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not available in production.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user.is_doctor = True
    db.commit()
    db.refresh(user)
    return _build_user_response(user)
