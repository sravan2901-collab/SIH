"""Unit tests for backend/app/auth/jwt.py — no external services required."""
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.auth.jwt import create_access_token, decode_token


def test_create_and_decode_roundtrip():
    token = create_access_token(
        data={"sub": "some-user-id", "role": "Admin"},
        expires_delta=timedelta(minutes=30),
    )
    payload = decode_token(token)
    assert payload["sub"] == "some-user-id"
    assert payload["role"] == "Admin"
    assert "exp" in payload


def test_decode_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not.a.valid.token")
    assert exc_info.value.status_code == 401


def test_decode_token_expired_raises_401():
    expired_token = create_access_token(
        data={"sub": "some-user-id", "role": "Inspector"},
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(expired_token)
    assert exc_info.value.status_code == 401


def test_decode_token_wrong_signature_raises_401():
    from jose import jwt as jose_jwt

    bad_token = jose_jwt.encode(
        {"sub": "x", "role": "Admin"}, "a-completely-different-key", algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(bad_token)
    assert exc_info.value.status_code == 401
