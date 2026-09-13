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


def test_register_schema_validation():
    import pytest
    from pydantic import ValidationError
    from app.schemas import RegisterRequest

    for bad_pwd in ("", "short"):
        with pytest.raises(ValidationError):
            RegisterRequest(name="Name", email="test@lmpc.gov", password=bad_pwd, role="Inspector")

    for bad_name in ("", "   "):
        with pytest.raises(ValidationError):
            RegisterRequest(name=bad_name, email="test@lmpc.gov", password="ValidPass123!", role="Inspector")


def test_product_create_schema_validation():
    import pytest
    from pydantic import ValidationError
    from schemas.product import ProductCreate

    for bad_name in ("", "   "):
        with pytest.raises(ValidationError):
            ProductCreate(name=bad_name)
