"""
Tests for the payment-facing routes in blueprints/xendit.py:
  - create_checkout  (POST /api/checkout)
  - cancel_subscription (POST /api/cancel-subscription)

Mocking strategy
  * blueprints.xendit.get_authenticated_user_id  — controls auth
  * blueprints.xendit._get_db                    — avoids real DB (psycopg3 pool)
  * blueprints.xendit._with_retry                — avoids real HTTP to Xendit
  * blueprints.xendit._ensure_user_exists        — side-effect-free stub
  * requests.post (for cancel_subscription)      — avoids real HTTP

DB mock notes:
  The conftest mock_conn models psycopg3:
    conn.__enter__ returns conn itself
    conn.cursor() returns cur (also a context-manager whose __enter__ returns cur)
  This matches the `with _get_db() as conn: with conn.cursor() as cur:` pattern.
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from blueprints.xendit import create_checkout, cancel_subscription


# ── Shared auth constants ─────────────────────────────────────────────────────

_AUTH = {"Authorization": "Bearer fake-token"}
_AUTHED = ("user_abc123", None)
_UNAUTHED = (None, "Missing Authorization Header")


# ── create_checkout ───────────────────────────────────────────────────────────

def test_checkout_returns_401_when_unauthenticated(make_request):
    req = make_request(method="POST", body={"plan_key": "amicus_monthly"})
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = create_checkout(req)
    assert resp.status_code == 401


def test_checkout_returns_400_for_missing_plan_key(make_request):
    req = make_request(method="POST", headers=_AUTH, body={})
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit.config") as mock_cfg:
        mock_cfg.XENDIT_BYPASS = False
        mock_cfg.XENDIT_API_KEY = "sk_real_key"
        resp = create_checkout(req)
    assert resp.status_code == 400
    assert "plan_key" in json.loads(resp.get_body())["error"].lower()


def test_checkout_returns_400_for_unknown_plan_key(make_request):
    req = make_request(method="POST", headers=_AUTH, body={"plan_key": "nonexistent_plan"})
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit.config") as mock_cfg:
        mock_cfg.XENDIT_BYPASS = False
        mock_cfg.XENDIT_API_KEY = "sk_real_key"
        resp = create_checkout(req)
    assert resp.status_code == 400


def test_checkout_returns_503_when_api_key_missing(make_request):
    """When XENDIT_API_KEY is empty and bypass is off, return 503 with a clear error."""
    req = make_request(method="POST", headers=_AUTH, body={"plan_key": "amicus_monthly"})
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit.config.XENDIT_API_KEY", ""), \
         patch("blueprints.xendit.XENDIT_BYPASS", False):
        resp = create_checkout(req)
    assert resp.status_code == 503


def test_checkout_bypass_mode_grants_tier_immediately(make_request, mock_conn):
    """When XENDIT_BYPASS=True the route skips Xendit and upgrades the user in DB."""
    conn, cur = mock_conn
    req = make_request(method="POST", headers=_AUTH, body={"plan_key": "amicus_monthly"})
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit.XENDIT_BYPASS", True), \
         patch("blueprints.xendit._get_db", return_value=conn):
        resp = create_checkout(req)
    assert resp.status_code == 200
    body = json.loads(resp.get_body())
    assert body.get("bypass") is True
    assert body.get("tier") == "amicus"


def test_checkout_returns_checkout_url_on_success(make_request, mock_conn):
    """Happy path: Xendit returns a payment_link_url, route returns it as checkout_url."""
    conn, cur = mock_conn
    # First fetchone: SELECT email, first_name, last_name, xendit_customer_id
    cur.fetchone.return_value = ("user@test.com", "Juan", "dela Cruz", None)

    xendit_resp = MagicMock()
    xendit_resp.status_code = 201
    xendit_resp.json.return_value = {
        "payment_link_url": "https://checkout.xendit.co/pay/session_abc",
        "payment_session_id": "ps_001",
    }

    req = make_request(method="POST", headers=_AUTH, body={"plan_key": "amicus_monthly"})
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit.XENDIT_BYPASS", False), \
         patch("blueprints.xendit.config.XENDIT_API_KEY", "sk_live_key"), \
         patch("blueprints.xendit._ensure_user_exists"), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit.xendit_post", return_value=xendit_resp):
        resp = create_checkout(req)

    assert resp.status_code == 200
    body = json.loads(resp.get_body())
    assert body["checkout_url"] == "https://checkout.xendit.co/pay/session_abc"
    assert body["plan_key"] == "amicus_monthly"


# ── cancel_subscription ───────────────────────────────────────────────────────

def test_cancel_returns_401_when_unauthenticated(make_request):
    req = make_request(method="POST")
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_UNAUTHED):
        resp = cancel_subscription(req)
    assert resp.status_code == 401


def test_cancel_returns_404_when_no_active_subscription(make_request, mock_conn):
    """User has no plan_id and is not a paid Xendit subscriber — return 404."""
    conn, cur = mock_conn
    # (xendit_plan_id, subscription_source, subscription_tier, email)
    cur.fetchone.return_value = (None, "free", "free", "user@test.com")

    req = make_request(method="POST", headers=_AUTH)
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit._get_db", return_value=conn):
        resp = cancel_subscription(req)
    assert resp.status_code == 404


def test_cancel_returns_404_when_user_not_found(make_request, mock_conn):
    conn, cur = mock_conn
    cur.fetchone.return_value = None  # user row missing entirely

    req = make_request(method="POST", headers=_AUTH)
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit._get_db", return_value=conn):
        resp = cancel_subscription(req)
    assert resp.status_code == 404


def test_cancel_succeeds_and_marks_subscription_cancelled(make_request, mock_conn):
    """
    Happy path: user has a xendit_plan_id, Xendit deactivate returns 200,
    DB is updated to 'cancelled', route returns 200 ok=True.
    """
    conn, cur = mock_conn
    expires = datetime(2026, 7, 1, tzinfo=timezone.utc)
    cur.fetchone.side_effect = [
        # 1st call: SELECT xendit_plan_id, subscription_source, subscription_tier, email
        ("rp_live_abc", "xendit", "amicus", "user@test.com"),
        # 2nd call: SELECT subscription_expires_at
        (expires,),
    ]

    cancel_resp = MagicMock()
    cancel_resp.status_code = 200
    cancel_resp.json.return_value = {"id": "rp_live_abc", "status": "INACTIVE"}

    req = make_request(method="POST", headers=_AUTH)
    with patch("blueprints.xendit.get_authenticated_user_id", return_value=_AUTHED), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit.xendit_post", return_value=cancel_resp), \
         patch("blueprints.xendit.send_cancellation_email"):
        resp = cancel_subscription(req)

    assert resp.status_code == 200
    body = json.loads(resp.get_body())
    # Response contains message + access_until + xendit_deactivated flag
    assert "message" in body
    assert body.get("xendit_deactivated") is True
    assert "access_until" in body
    # DB UPDATE should have been called (commit invoked)
    conn.commit.assert_called()
