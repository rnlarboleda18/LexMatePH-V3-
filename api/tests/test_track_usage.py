"""
track_usage — critical paths:
  1. Subscription tier enforcement (paid/admin users bypass the quota)
  2. Free-tier daily cap (advisory-locked counter)
  3. Unknown features rejected with 400
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from blueprints.xendit import track_usage


ENV = {
    "DB_CONNECTION_STRING": "postgresql://test",
    "XENDIT_API_KEY": "test_key",
}

CLERK_ID = "user_test_abc"


def _authed_request(make_request, body):
    """Request that looks authenticated (has an Authorization header)."""
    return make_request(
        method="POST",
        body=body,
        headers={"Authorization": "Bearer fake.jwt.token"},
    )


def _unauthed_request(make_request, body):
    return make_request(method="POST", body=body)


# ── Input validation ──────────────────────────────────────────────────────────

def test_unknown_feature_returns_400(make_request):
    req = _unauthed_request(make_request, {"feature": "not_a_real_feature"})
    with patch.dict(os.environ, ENV):
        resp = track_usage(req)
    assert resp.status_code == 400
    assert "Unknown feature" in resp.get_body().decode()


# ── Paid-tier bypass ──────────────────────────────────────────────────────────

def test_paid_tier_user_always_allowed(make_request, mock_conn):
    """Amicus (or any paid) tier user is allowed without touching quota counters."""
    conn, cur = mock_conn
    cur.fetchone.return_value = ("amicus", False)  # (tier, is_admin)

    req = _authed_request(make_request, {"feature": "case_digest"})
    with patch.dict(os.environ, ENV), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit.get_authenticated_user_id", return_value=(CLERK_ID, None)):
        resp = track_usage(req)

    body = json.loads(resp.get_body())
    assert resp.status_code == 200
    assert body["allowed"] is True
    assert body["limit"] == -1


def test_admin_user_always_allowed(make_request, mock_conn):
    """Admin flag bypasses quota regardless of subscription tier."""
    conn, cur = mock_conn
    cur.fetchone.return_value = ("free", True)  # free tier but is_admin=True

    req = _authed_request(make_request, {"feature": "case_digest"})
    with patch.dict(os.environ, ENV), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit.get_authenticated_user_id", return_value=(CLERK_ID, None)):
        resp = track_usage(req)

    body = json.loads(resp.get_body())
    assert resp.status_code == 200
    assert body["allowed"] is True
    assert body["is_admin"] is True


# ── Free-tier quota ───────────────────────────────────────────────────────────

def test_free_tier_within_limit_allowed(make_request, mock_conn):
    """Free-tier user with 3/5 uses today is allowed and count increments."""
    conn, cur = mock_conn
    # fetchone() call 1: tier check → free, not admin
    # fetchone() call 2: advisory lock (no fetchone), COUNT → 3
    cur.fetchone.side_effect = [("free", False), (3,)]

    req = _authed_request(make_request, {"feature": "case_digest"})
    with patch.dict(os.environ, ENV), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit.get_authenticated_user_id", return_value=(CLERK_ID, None)):
        resp = track_usage(req)

    body = json.loads(resp.get_body())
    assert resp.status_code == 200
    assert body["allowed"] is True
    assert body["used"] == 4  # 3 + 1 after insert
    assert body["limit"] == 5


def test_free_tier_at_limit_denied(make_request, mock_conn):
    """Free-tier user at the daily cap (5/5) is denied."""
    conn, cur = mock_conn
    cur.fetchone.side_effect = [("free", False), (5,)]

    req = _authed_request(make_request, {"feature": "case_digest"})
    with patch.dict(os.environ, ENV), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit.get_authenticated_user_id", return_value=(CLERK_ID, None)):
        resp = track_usage(req)

    body = json.loads(resp.get_body())
    assert resp.status_code == 200
    assert body["allowed"] is False
    assert body["used"] == 5
    assert body["limit"] == 5


def test_free_tier_at_limit_does_not_insert_usage(make_request, mock_conn):
    """When the cap is hit the usage INSERT must NOT run (quota not double-counted)."""
    conn, cur = mock_conn
    cur.fetchone.side_effect = [("free", False), (5,)]

    req = _authed_request(make_request, {"feature": "case_digest"})
    with patch.dict(os.environ, ENV), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit.get_authenticated_user_id", return_value=(CLERK_ID, None)):
        track_usage(req)

    # INSERT INTO usage_logs must not have been called
    insert_calls = [
        c for c in cur.execute.call_args_list
        if "INSERT INTO usage_logs" in str(c)
    ]
    assert len(insert_calls) == 0
