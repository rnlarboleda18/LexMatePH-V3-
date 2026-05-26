"""Tests for POST /api/track-usage (blueprints/xendit.py).

Covers:
- Unknown feature rejected with 400
- Paid user always allowed (no metering, limit=-1)
- Admin user always allowed
- Free signed-in user: allowed when under daily cap
- Free signed-in user: denied when at daily cap
- Anonymous user: allowed within 24-hour guest window
- Anonymous user: denied after guest window + over daily cap
- Missing anonymousId when not signed in → 400
- Bad auth token with no anon id → 401
"""
import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from tests.conftest import (
    make_auth_request, make_request, parse_response,
    make_db, MockCursor, MockConnection,
)

VALID_FEATURE = "case_digest"
FREE_DAILY_LIMIT = 5
VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"  # RFC 4122 UUID for anonymous tests


def _make_conn_with_txn(cursor: MockCursor) -> MockConnection:
    """Wrap a cursor in a MockConnection that has a working transaction() context manager."""
    conn = MockConnection(cursor=cursor)

    @contextmanager
    def _txn():
        yield

    conn.transaction = _txn
    return conn


def _call(req, db_conn=None, clerk_result=None):
    from blueprints.xendit import track_usage

    if db_conn is None:
        db_conn = make_db()

    patches = [
        patch("blueprints.xendit._get_db", return_value=db_conn),
    ]
    if clerk_result is not None:
        patches.append(
            patch("blueprints.xendit.get_authenticated_user_id", return_value=clerk_result)
        )

    ctx = patches[0]
    for p in patches[1:]:
        ctx = ctx.__class__.__new__(ctx.__class__)
    # simpler: use nested with via contextlib
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        return track_usage(req)


# ── Input validation ──────────────────────────────────────────────────────────

def test_unknown_feature_returns_400():
    req = make_auth_request(
        body={"feature": "not_a_real_feature"},
        clerk_id="user_free",
    )
    resp = _call(req, clerk_result=("user_free", None))
    status, body = parse_response(resp)
    assert status == 400
    assert "Unknown feature" in body["error"]


def test_missing_feature_returns_400():
    req = make_auth_request(body={}, clerk_id="user_free")
    resp = _call(req, clerk_result=("user_free", None))
    status, body = parse_response(resp)
    assert status == 400


# ── Paid tier bypass ──────────────────────────────────────────────────────────

def test_paid_user_always_allowed():
    db = make_db(rows=[("amicus", False)])
    req = make_auth_request(body={"feature": VALID_FEATURE})
    resp = _call(req, db_conn=db, clerk_result=("user_paid", None))
    status, body = parse_response(resp)
    assert status == 200
    assert body["allowed"] is True
    assert body["limit"] == -1


def test_admin_user_always_allowed():
    db = make_db(rows=[("free", True)])  # is_admin=True
    req = make_auth_request(body={"feature": VALID_FEATURE})
    resp = _call(req, db_conn=db, clerk_result=("user_admin", None))
    status, body = parse_response(resp)
    assert status == 200
    assert body["allowed"] is True
    assert body["is_admin"] is True


# ── Free signed-in user ───────────────────────────────────────────────────────

def test_free_user_allowed_when_under_limit():
    # Two sequential fetchone calls: first→user tier row, second→usage count
    cur = MockCursor()
    cur.rows = [("free", False), (2,)]
    db = _make_conn_with_txn(cur)
    req = make_auth_request(body={"feature": VALID_FEATURE})
    resp = _call(req, db_conn=db, clerk_result=("user_free", None))
    status, body = parse_response(resp)
    assert status == 200
    assert body["allowed"] is True
    assert body["used"] == 3  # 2 previous + this request


def test_free_user_denied_when_at_limit():
    cur = MockCursor()
    cur.rows = [("free", False), (FREE_DAILY_LIMIT,)]
    db = _make_conn_with_txn(cur)
    req = make_auth_request(body={"feature": VALID_FEATURE})
    resp = _call(req, db_conn=db, clerk_result=("user_free2", None))
    status, body = parse_response(resp)
    assert status == 200
    assert body["allowed"] is False
    assert body["used"] == FREE_DAILY_LIMIT


# ── Anonymous user ────────────────────────────────────────────────────────────

def test_anonymous_first_request_is_in_guest_window():
    # first_seen=None → brand-new anonymous user → guest window active → unlimited
    cur = MockCursor()
    cur.rows = [(None,), (0,)]  # MIN(created_at)=None, COUNT=0
    db = _make_conn_with_txn(cur)
    req = make_request("POST", body={"feature": VALID_FEATURE, "anonymousId": VALID_UUID})
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["allowed"] is True
    assert body.get("guest_window") is True


def test_anonymous_user_over_limit_after_guest_window():
    from datetime import datetime, timezone, timedelta
    old_first_seen = datetime.now(timezone.utc) - timedelta(hours=48)
    cur = MockCursor()
    cur.rows = [(old_first_seen,), (FREE_DAILY_LIMIT + 1,)]
    db = _make_conn_with_txn(cur)
    req = make_request("POST", body={"feature": VALID_FEATURE, "anonymousId": VALID_UUID})
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["allowed"] is False


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_no_auth_and_no_anonymous_id_returns_400():
    req = make_request("POST", body={"feature": VALID_FEATURE})
    resp = _call(req)
    status, body = parse_response(resp)
    assert status == 400
    assert "anonymousId" in body["error"]


def test_bad_auth_header_returns_401():
    req = make_auth_request(body={"feature": VALID_FEATURE})
    resp = _call(req, clerk_result=(None, "Token expired"))
    status, body = parse_response(resp)
    assert status == 401
