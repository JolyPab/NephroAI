"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from database import User, SessionLocal
from auth import get_password_hash, verify_password, create_access_token, get_current_user_id

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    role: str = "PATIENT"  # Added for frontend compatibility


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user."""
    print(f"[DEBUG] Registration: email={user_data.email}, full_name={user_data.full_name}, is_doctor={user_data.is_doctor}")
    
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name or user_data.email.split('@')[0],  # Default
        is_doctor=user_data.is_doctor
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    print(f"[DEBUG] User created: id={db_user.id}")
    
    # Create access token
    access_token = create_access_token(data={"sub": db_user.id})
    
    # Return user + token for frontend
    return AuthResponse(
        accessToken=access_token,
        user=UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            is_doctor=db_user.is_doctor,
            is_active=db_user.is_active,
            role="DOCTOR" if db_user.is_doctor else "PATIENT"
        )
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
            detail="User is inactive"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    # Return user + token for frontend
    return AuthResponse(
        accessToken=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_doctor=user.is_doctor,
            is_active=user.is_active,
            role="DOCTOR" if user.is_doctor else "PATIENT"
        )
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
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_doctor=user.is_doctor,
        is_active=user.is_active,
        role="DOCTOR" if user.is_doctor else "PATIENT"
    )


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
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_doctor=user.is_doctor,
        is_active=user.is_active,
        role="DOCTOR"
    )
