"""Tests for CORS allowlist, rate limiting on /auth/login, and TLS redirect middleware."""
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.limiter import limiter


def test_cors_allowed_origin(client):
    """Requests from allowed origin receive Access-Control-Allow-Origin header."""
    resp = client.options(
        "/products/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    # Credentials must not be true for bearer token auth
    assert resp.headers.get("access-control-allow-credentials") != "true"


def test_cors_unallowed_origin_rejected(client):
    """Requests from disallowed origin do not receive Access-Control-Allow-Origin header."""
    resp = client.options(
        "/products/health",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example"


def test_rate_limit_exceeded_returns_429(client, monkeypatch):
    """When enabled, exceeding 10 requests/minute on /auth/login returns 429 with detail."""
    monkeypatch.setattr(limiter, "enabled", True)

    async def mock_get_db():
        class MockResult:
            def scalar_one_or_none(self):
                return None

        class MockSession:
            async def execute(self, *args, **kwargs):
                return MockResult()

        yield MockSession()

    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = mock_get_db
    try:
        hit_429 = False
        last_resp = None

        # Limit is 10/minute, so 15 attempts will hit the limiter
        for _ in range(15):
            resp = client.post(
                "/auth/login",
                json={"email": "nobody@lmpc.gov", "password": "wrongpassword"},
            )
            last_resp = resp
            if resp.status_code == 429:
                hit_429 = True
                break

        assert hit_429, f"Expected 429 status code but last response was {last_resp.status_code if last_resp else None}"
        assert "detail" in last_resp.json()
        assert "Rate limit exceeded" in last_resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_tls_redirect_middleware_behavior():
    """Verify HTTPSRedirectMiddleware redirects HTTP requests to HTTPS."""
    async def homepage(request):
        return PlainTextResponse("OK")

    test_app = Starlette(routes=[Route("/", homepage)])
    test_app.add_middleware(HTTPSRedirectMiddleware)

    with TestClient(test_app, base_url="http://testserver") as test_client:
        resp = test_client.get("/", follow_redirects=False)
        assert resp.status_code in (301, 307, 308)
        assert resp.headers["location"].startswith("https://")
