"""Authentication utilities."""

from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key-change-this-in-production"  # TODO: move to .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    # Ensure 'sub' is a string (jose library requirement)
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(f"[DEBUG] Token created for: {data}")
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode JWT token."""
    try:
        print(f"[DEBUG] Decoding token with SECRET_KEY={SECRET_KEY[:10]}..., ALGORITHM={ALGORITHM}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"[DEBUG] Token decoded OK: {payload}")
        return payload
    except JWTError as e:
        print(f"[DEBUG] JWT decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Get current user ID from JWT token."""
    print(f"[DEBUG] get_current_user_id: token received (first 20 chars): {credentials.credentials[:20]}...")
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        print(f"[DEBUG] Token decoded successfully: {payload}")
        
        sub = payload.get("sub")
        if sub is None:
            print(f"[DEBUG] ERROR: No 'sub' in token payload!")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        
        # Convert string to int (jose stores sub as string)
        user_id: int = int(sub) if isinstance(sub, str) else sub
        print(f"[DEBUG] User ID from token: {user_id}")
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Unexpected error in get_current_user_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization error: {str(e)}",
        )

