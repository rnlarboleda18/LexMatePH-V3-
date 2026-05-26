"""Tests for GET /api/subscription-status (blueprints/xendit.py).

Covers:
- Unauthorized access (missing/invalid token)
- Free tier user
- Paid (amicus/juris) tier user
- Admin user via is_admin DB flag
- Admin user via hardcoded email list (documents current behavior)
- User not found in DB (returns free tier default)
- can_cancel_xendit flag for paid/admin/free users
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import (
    make_auth_request, make_request, parse_response,
    make_db, user_row, paid_user_row, admin_user_row,
)


ANON_EMAIL = "test@example.com"


def _two_call_db(admin_email_row: tuple, full_user_row: tuple) -> object:
    """Build a DB mock that handles subscription_status's two _get_db() calls.

    First call: SELECT is_admin, email (2 cols)
    Second call: SELECT subscription_tier, ... (9 cols)
    Both calls share the same MockConnection and cursor, so rows are consumed in order.
    """
    return make_db(rows=[admin_email_row, full_user_row])


def _call(req, db_conn=None, clerk_result=("user_test123", None)):
    """Call subscription_status with patched DB and Clerk auth."""
    from blueprints.xendit import subscription_status

    if db_conn is None:
        db_conn = _two_call_db(
            (False, ANON_EMAIL),
            user_row(),
        )

    with patch("blueprints.xendit._get_db", return_value=db_conn), \
         patch("blueprints.xendit._ensure_user_exists"), \
         patch("blueprints.xendit.get_authenticated_user_id", return_value=clerk_result), \
         patch("blueprints.xendit.expire_trial_for_user"), \
         patch("blueprints.xendit.expire_cancelled_xendit_sub"), \
         patch("blueprints.xendit.expire_past_due_xendit_sub"), \
         patch("blueprints.xendit.expire_founding_promo_for_user"), \
         patch("blueprints.xendit.try_grant_founding_promo"), \
         patch("blueprints.xendit.claim_trial_ending_reminder", return_value=None), \
         patch("blueprints.xendit.trial_reminder_hours_before_end", return_value=24), \
         patch("blueprints.xendit.past_due_grace_days", return_value=3):
        return subscription_status(req)


# ── Auth tests ────────────────────────────────────────────────────────────────

def test_returns_401_when_no_auth_header():
    req = make_request("GET")
    resp = _call(req, clerk_result=(None, "Missing Authorization Header"))
    status, body = parse_response(resp)
    assert status == 401


def test_returns_401_when_token_expired():
    req = make_auth_request()
    resp = _call(req, clerk_result=(None, "Token expired"))
    status, body = parse_response(resp)
    assert status == 401
    assert "error" in body


# ── Free tier ─────────────────────────────────────────────────────────────────

def test_free_tier_user_returns_free():
    db = _two_call_db(
        (False, ANON_EMAIL),
        user_row(tier="free", status="inactive"),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["tier"] == "free"
    assert body["is_admin"] is False


def test_user_not_in_db_returns_free_defaults():
    # First call returns no row; second call also returns no row → free defaults
    db = make_db(rows=[])
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["tier"] == "free"
    assert body["is_admin"] is False


# ── Paid tier ─────────────────────────────────────────────────────────────────

def test_amicus_tier_user():
    db = _two_call_db(
        (False, ANON_EMAIL),
        paid_user_row(tier="amicus"),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["tier"] == "amicus"
    assert body["status"] == "active"


def test_juris_tier_user():
    db = _two_call_db(
        (False, ANON_EMAIL),
        paid_user_row(tier="juris"),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["tier"] == "juris"


# ── Admin via DB flag ─────────────────────────────────────────────────────────

def test_admin_flag_from_db_is_admin():
    row = admin_user_row()
    db = _two_call_db(
        (True, ANON_EMAIL),  # is_admin=True, email
        row,
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["is_admin"] is True


# ── Admin status is DB-only (Tier 2 security fix applied) ─────────────────────

def test_admin_email_without_db_flag_is_not_admin():
    # Admin status comes solely from the DB is_admin column after Tier 2 fix.
    # A known admin email with is_admin=False in DB must NOT be granted admin.
    admin_email = "rnlarboleda18@gmail.com"
    db = _two_call_db(
        (False, admin_email),
        user_row(tier="amicus", status="active", is_admin=False, email=admin_email),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["is_admin"] is False  # DB flag is authoritative; email alone does not grant admin


def test_non_admin_email_is_not_admin():
    email = "notanadmin@example.com"
    db = _two_call_db(
        (False, email),
        user_row(tier="free", status="inactive", is_admin=False, email=email),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["is_admin"] is False


# ── can_cancel_xendit flag ────────────────────────────────────────────────────

def test_can_cancel_xendit_true_for_paid_non_admin():
    db = _two_call_db(
        (False, ANON_EMAIL),
        paid_user_row(),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["can_cancel_xendit"] is True


def test_can_cancel_xendit_false_for_admin():
    db = _two_call_db(
        (True, ANON_EMAIL),
        admin_user_row(),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["can_cancel_xendit"] is False


def test_can_cancel_xendit_false_for_free_user():
    db = _two_call_db(
        (False, ANON_EMAIL),
        user_row(tier="free"),
    )
    req = make_auth_request()
    resp = _call(req, db_conn=db)
    status, body = parse_response(resp)
    assert status == 200
    assert body["can_cancel_xendit"] is False
