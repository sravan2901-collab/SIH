"""JWT access token utilities for the LMPC Compliance System.

Uses python-jose[cryptography] with HS256. SECRET_KEY is read from the
environment; the fallback below is dev-only and must be rotated before
any shared/non-local deployment.

Typical usage from a login endpoint:
    token = create_access_token(
        data={"sub": str(user.user_id), "role": user.role},
        expires_delta=timedelta(minutes=30),
    )
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt

# NOTE: dev-only fallback secret. Rotate before any shared/non-local
# deployment — set a real SECRET_KEY in the environment instead.
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "e4de0bdde026f26a2f819007473bda31ad44a1339bac70472fd0720727092ce0",
)
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Encode `data` as a signed JWT, adding an `exp` claim.

    Callers building a login response typically pass
    data={"sub": str(user_id), "role": role}.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT, raising HTTPException(401) if invalid or expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
