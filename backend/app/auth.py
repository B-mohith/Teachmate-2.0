from datetime import datetime, timedelta, timezone
import os
from typing import Optional
import uuid

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
import app.models as models

load_dotenv()

# Configuration Settings
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_change_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing instance using modern pwdlib with Bcrypt
password_hash = PasswordHash((BcryptHasher(),))

# OAuth2 scheme: tells FastAPI that token requests hit POST /auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ==========================================
# 1. PASSWORD UTILITIES
# ==========================================

def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt."""
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored bcrypt hash."""
    return password_hash.verify(plain_password, hashed_password)


# ==========================================
# 2. JWT TOKEN MANAGEMENT
# ==========================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Encode payload dict into a signed JWT access token with an expiration time."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ==========================================
# 3. CURRENT USER DEPENDENCY
# ==========================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    """
    Decodes the incoming Bearer JWT token, validates its signature/expiration,
    and returns the corresponding User model from PostgreSQL.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode and verify token signature + expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    # Query PostgreSQL for the user ID extracted from the token
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if user is None:
        raise credentials_exception

    return user