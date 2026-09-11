"""Unit tests for the role-gating dependencies in backend/app/auth/dependencies.py.

require_inspector and require_reviewer_or_admin are pure role checks and are
tested here with a lightweight stand-in object (anything with a `.role`
attribute) — no database needed.

get_current_user is NOT unit-tested here: it queries the real `users` table,
so testing it meaningfully requires a reachable, migrated Postgres. That is
verified live against the running stack instead (see task report), rather
than committed as a test that would fail in any environment without a
database, unlike every other test in this suite.
"""
import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_inspector, require_reviewer_or_admin


class _StubUser:
    def __init__(self, role: str):
        self.role = role


def test_require_inspector_allows_inspector():
    user = _StubUser("Inspector")
    assert require_inspector(user) is user


def test_require_inspector_blocks_non_inspector():
    for role in ("Reviewer", "Admin"):
        with pytest.raises(HTTPException) as exc_info:
            require_inspector(_StubUser(role))
        assert exc_info.value.status_code == 403


def test_require_reviewer_or_admin_allows_reviewer_and_admin():
    for role in ("Reviewer", "Admin"):
        user = _StubUser(role)
        assert require_reviewer_or_admin(user) is user


def test_require_reviewer_or_admin_blocks_inspector():
    with pytest.raises(HTTPException) as exc_info:
        require_reviewer_or_admin(_StubUser("Inspector"))
    assert exc_info.value.status_code == 403
