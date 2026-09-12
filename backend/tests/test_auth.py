"""Integration tests for the /auth endpoints and role gating.

Unlike test_dependencies.py, these tests DO require a real, migrated Postgres
reachable via DATABASE_URL: get_current_user and the login/register endpoints
query the real `users` table. The CI `test` job already provisions this
(postgres service + `alembic upgrade head` before `pytest`); locally, start
the stack's `db` service and run migrations first.
"""
import asyncio
import uuid

import asyncpg
import pytest
from fastapi import Depends

from app.auth.dependencies import require_reviewer_or_admin
from app.database import DATABASE_URL
from app.main import app

ADMIN_EMAIL = "admin@lmpc.gov"
# Dev-only seed credential — see alembic/versions/164db70a116d_seed_admin_user.py
ADMIN_PASSWORD = "ChangeMe_Dev_Only!123"

pytestmark = pytest.mark.integration


async def _delete_user_by_email(email: str) -> None:
    # Deliberately NOT using the app's pooled async engine (app.database.engine):
    # that engine is a module-level singleton bound to whichever event loop
    # first used it (the TestClient's, via the `client` fixture). asyncio.run()
    # here opens a *different* loop, and asyncpg connections can't cross loops
    # — reusing the pooled engine raised `AttributeError: 'NoneType' object has
    # no attribute '_init_types'` deep in asyncpg. A standalone connection,
    # opened and closed entirely within this one call, avoids that.
    conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
    try:
        await conn.execute("DELETE FROM users WHERE email = $1", email)
    finally:
        await conn.close()


@pytest.fixture(scope="module")
def admin_token(client):
    resp = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def inspector_token(client, admin_token):
    email = f"pytest.inspector.{uuid.uuid4().hex[:8]}@lmpc.gov"
    reg = client.post(
        "/auth/register",
        json={
            "name": "Pytest Inspector",
            "email": email,
            "password": "TempPass!123",
            "role": "Inspector",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reg.status_code == 201

    login = client.post(
        "/auth/login", json={"email": email, "password": "TempPass!123"}
    )
    assert login.status_code == 200

    yield login.json()["access_token"]

    asyncio.run(_delete_user_by_email(email))


def test_valid_credentials_returns_200_and_token(client, admin_token):
    # admin_token fixture already proves 200 + a token; assert the shape too.
    assert isinstance(admin_token, str) and len(admin_token) > 0


def test_wrong_password_returns_401(client):
    resp = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password"


def test_no_token_on_protected_route_returns_401(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def _reviewer_only_probe(user=Depends(require_reviewer_or_admin)):
    return {"ok": True}


# No route in the app currently uses require_reviewer_or_admin (products/scans/
# reports/dashboard are still health-check stubs), so this adds one throwaway
# test-only route to the real app to exercise that dependency over real HTTP,
# reusing the existing `client` fixture/event loop rather than opening a second
# TestClient (a second TestClient here previously segfaulted: asyncpg's async
# engine is a module-level singleton and isn't safe to drive from two event
# loops at once).
app.add_api_route("/_test_reviewer_only", _reviewer_only_probe, methods=["GET"])


def test_inspector_token_on_reviewer_route_returns_403(client, inspector_token):
    resp = client.get(
        "/_test_reviewer_only",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Reviewer or Admin role required"
