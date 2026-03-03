"""Authentication routes."""

import datetime as dt
import hashlib
import hmac
import logging
import os
import random
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import EmailVerificationCode, User, SessionLocal
from backend.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_id,
)
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


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_email_code(code: str) -> str:
    digest = hashlib.sha256(f"{EMAIL_CODE_SALT}:{code}".encode("utf-8")).hexdigest()
    return digest


def _generate_email_code() -> str:
    generator = random.SystemRandom()
    return f"{generator.randint(0, 999999):06d}"


def _create_verification_code(db: Session, user: User) -> EmailVerificationCode:
    now = dt.datetime.utcnow()
    one_hour_ago = now - dt.timedelta(hours=1)
    recent_sends = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == user.email,
            EmailVerificationCode.created_at >= one_hour_ago,
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


def _build_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_doctor=user.is_doctor,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
        role="DOCTOR" if user.is_doctor else "PATIENT",
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user and send email verification code."""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email."
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
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
        return AuthResponse(accessToken=access_token, user=_build_user_response(user))

    code_row = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.used_at.is_(None),
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
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    user.email_verified_at = now
    user.is_active = True
    code_row.used_at = now
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
    """Mark current user as doctor (helper endpoint)."""
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
