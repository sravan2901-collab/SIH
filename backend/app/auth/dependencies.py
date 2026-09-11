"""FastAPI dependency functions for authentication and role-based access control."""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.database import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the bearer token and load the corresponding User row."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user


def require_inspector(user: User = Depends(get_current_user)) -> User:
    """Gate a route to Inspector-role users only."""
    if user.role != "Inspector":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inspector role required",
        )
    return user


def require_reviewer_or_admin(user: User = Depends(get_current_user)) -> User:
    """Gate a route to Reviewer- or Admin-role users."""
    if user.role not in ("Reviewer", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer or Admin role required",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Gate a route to Admin-role users only."""
    if user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
