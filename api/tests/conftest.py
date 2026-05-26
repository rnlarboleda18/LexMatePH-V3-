"""Shared pytest fixtures for LexMatePH API tests.

Provides mock factories for azure.functions HTTP objects, database connections,
and Clerk auth — so blueprints can be tested in isolation without real external deps.

NOTE: System pyjwt/cryptography on this host have a broken Rust native lib.
We mock jwt and all utils.* modules at sys.modules level before any blueprint
is imported, so tests never touch the real cryptography code.
"""
import json
import sys
import os
import pytest
from unittest.mock import MagicMock
from contextlib import contextmanager

# ── Pre-import sys.modules mocks (must happen before any blueprint import) ────
# These prevent the system jwt/cryptography native lib crash.

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_mock_jwt = MagicMock()
_mock_jwt.ExpiredSignatureError = type("ExpiredSignatureError", (Exception,), {})
_mock_jwt.PyJWKClient = MagicMock
_mock_jwt.decode = MagicMock(return_value={"sub": "user_test123"})
_mock_jwt.get_unverified_header = MagicMock(return_value={"alg": "HS256"})
sys.modules.setdefault("jwt", _mock_jwt)
sys.modules.setdefault("cryptography", MagicMock())

_mock_clerk_auth = MagicMock()
_mock_clerk_auth.get_authenticated_user_id = MagicMock(return_value=("user_test123", None))
sys.modules.setdefault("utils.clerk_auth", _mock_clerk_auth)

# Mock heavy / network-touching utils so blueprints import cleanly
for _mod in ("utils.trial", "utils.founding_promo", "utils.email",
             "utils.gemini_rest", "utils.azure_speech_rest",
             "utils.ai_client", "utils.logging", "utils.codal_static_cache",
             "utils.flashcard_legal_concepts"):
    sys.modules.setdefault(_mod, MagicMock())

import azure.functions as func


# ── HTTP request / response helpers ───────────────────────────────────────────

def make_request(
    method: str = "GET",
    body=None,
    headers: dict | None = None,
    params: dict | None = None,
    route_params: dict | None = None,
) -> func.HttpRequest:
    """Build a minimal func.HttpRequest for unit tests."""
    if isinstance(body, dict):
        raw_body = json.dumps(body).encode()
    elif isinstance(body, str):
        raw_body = body.encode()
    elif isinstance(body, bytes):
        raw_body = body
    else:
        raw_body = b""

    return func.HttpRequest(
        method=method,
        url="https://localhost/api/test",
        headers=headers or {},
        params=params or {},
        route_params=route_params or {},
        body=raw_body,
    )


def make_auth_request(
    clerk_id: str = "user_test123",
    method: str = "GET",
    body=None,
    headers: dict | None = None,
    params: dict | None = None,
) -> func.HttpRequest:
    """Build a request with a fake Bearer token in the auth header."""
    hdrs = dict(headers or {})
    hdrs["Authorization"] = f"Bearer fake-token-for-{clerk_id}"
    return make_request(method=method, body=body, headers=hdrs, params=params)


def parse_response(resp: func.HttpResponse) -> tuple[int, dict]:
    """Return (status_code, parsed_json_body) from a func.HttpResponse."""
    return resp.status_code, json.loads(resp.get_body())


# ── Database mock factory ─────────────────────────────────────────────────────

class MockCursor:
    """Minimal psycopg cursor mock. Set .rows to control fetchone/fetchall output."""

    def __init__(self):
        self.rows: list = []
        self.rowcount: int = 1
        self._pos: int = 0
        self.executed: list[tuple] = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        if self._pos < len(self.rows):
            row = self.rows[self._pos]
            self._pos += 1
            return row
        return None

    def fetchall(self):
        result = self.rows[self._pos:]
        self._pos = len(self.rows)
        return result

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockConnection:
    """Minimal psycopg connection mock with context-manager and transaction support."""

    def __init__(self, cursor: "MockCursor | None" = None):
        self._cursor = cursor or MockCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self, *args, **kwargs):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass

    @contextmanager
    def transaction(self):
        yield

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *args):
        if exc_type:
            self.rolled_back = True
        else:
            self.committed = True


def make_db(rows: list | None = None, rowcount: int = 1) -> MockConnection:
    """Return a MockConnection whose cursor will yield `rows` on fetchone/fetchall."""
    cur = MockCursor()
    cur.rows = rows or []
    cur.rowcount = rowcount
    return MockConnection(cursor=cur)


# ── Standard user/subscription row fixtures ───────────────────────────────────

def user_row(
    tier: str = "free",
    status: str = "inactive",
    expires_at=None,
    is_admin: bool = False,
    email: str = "test@example.com",
    founding_slot=None,
    sub_source: str | None = None,
    xendit_plan_id: str | None = None,
    founding_granted_at=None,
) -> tuple:
    """Return a tuple matching the 9-column SELECT in subscription_status."""
    return (
        tier, status, expires_at, is_admin, email,
        founding_slot, sub_source, xendit_plan_id, founding_granted_at,
    )


def paid_user_row(tier: str = "amicus", **kwargs) -> tuple:
    return user_row(tier=tier, status="active", sub_source="xendit",
                    xendit_plan_id="xendit-plan-abc123", **kwargs)


def admin_user_row(**kwargs) -> tuple:
    return user_row(is_admin=True, tier="amicus", status="active", **kwargs)


# ── Pytest fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_clerk_ok(mocker):
    """Patch Clerk auth in blueprints.xendit to succeed."""
    return mocker.patch(
        "blueprints.xendit.get_authenticated_user_id",
        return_value=("user_test123", None),
    )


@pytest.fixture
def mock_clerk_fail(mocker):
    """Patch Clerk auth in blueprints.xendit to fail."""
    return mocker.patch(
        "blueprints.xendit.get_authenticated_user_id",
        return_value=(None, "Token expired"),
    )


@pytest.fixture
def mock_email(mocker):
    """Silence all outbound email sends."""
    mocker.patch("blueprints.xendit.send_cancellation_email", MagicMock())
    mocker.patch("blueprints.xendit.send_subscription_payment_past_due_email", MagicMock())
    mocker.patch("blueprints.xendit.send_trial_ending_reminder_email", MagicMock())


@pytest.fixture
def mock_trial_utils(mocker):
    """Patch trial utility functions bound in blueprints.xendit to no-ops."""
    mocker.patch("blueprints.xendit.expire_trial_for_user", MagicMock())
    mocker.patch("blueprints.xendit.expire_cancelled_xendit_sub", MagicMock())
    mocker.patch("blueprints.xendit.expire_past_due_xendit_sub", MagicMock())
    mocker.patch("blueprints.xendit.claim_trial_ending_reminder", return_value=None)
    mocker.patch("blueprints.xendit.trial_duration_hours", return_value=48)
    mocker.patch("blueprints.xendit.past_due_grace_days", return_value=3)
    mocker.patch("blueprints.xendit.trial_reminder_hours_before_end", return_value=24)


@pytest.fixture
def mock_founding_promo(mocker):
    """Patch founding promo helpers bound in blueprints.xendit to no-ops."""
    mocker.patch("blueprints.xendit.expire_founding_promo_for_user", MagicMock())
    mocker.patch("blueprints.xendit.try_grant_founding_promo", MagicMock())
