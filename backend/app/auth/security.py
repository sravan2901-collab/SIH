"""Password hashing utilities for the LMPC Compliance System.

Uses passlib's bcrypt handler. Hashes produced here are standard bcrypt
strings ($2b$...), fully interchangeable with hashes produced by the raw
`bcrypt` library used in the seed_admin_user Alembic migration — verified
compatible both directions before this module was written.
"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password for storage."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return pwd_context.verify(plain, hashed)
