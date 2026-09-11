"""Unit tests for backend/app/auth/security.py — no external services required."""
from app.auth.security import hash_password, verify_password


def test_hash_password_produces_bcrypt_hash():
    hashed = hash_password("Sup3rSecret!")
    assert hashed.startswith(("$2b$", "$2a$", "$2y$"))


def test_verify_password_correct():
    hashed = hash_password("Sup3rSecret!")
    assert verify_password("Sup3rSecret!", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("Sup3rSecret!")
    assert verify_password("WrongPassword", hashed) is False


def test_hash_password_is_salted():
    hash_one = hash_password("SamePassword")
    hash_two = hash_password("SamePassword")
    assert hash_one != hash_two
