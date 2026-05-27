"""
Clerk webhook — critical paths:
  1. Missing Svix headers → 400 (before any processing)
  2. Invalid Svix signature → 400 (forgery rejected)
  3. user.created → user row upserted in DB
  4. user.deleted → user row removed from DB
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from blueprints.clerk_webhook import clerk_webhook_core


ENV = {
    "CLERK_WEBHOOK_SECRET": "whsec_dGVzdF9zZWNyZXRfa2V5X2Zvcl91bml0X3Rlc3Rz",
    "DB_CONNECTION_STRING": "postgresql://test",
    "ADMIN_EMAILS": "admin@example.com",
}

_USER_CREATED_EVENT = {
    "type": "user.created",
    "data": {
        "id": "user_clerk_001",
        "email_addresses": [
            {"id": "ea_1", "email_address": "test@example.com"}
        ],
        "primary_email_address_id": "ea_1",
        "first_name": "Test",
        "last_name": "User",
        "unsafe_metadata": {},
    },
}

_USER_DELETED_EVENT = {
    "type": "user.deleted",
    "data": {"id": "user_clerk_001"},
}


def _svix_headers(msg_id="msg_001", timestamp="1234567890", signature="v1,fakesig"):
    return {
        "svix-id": msg_id,
        "svix-timestamp": timestamp,
        "svix-signature": signature,
    }


# ── Header validation ─────────────────────────────────────────────────────────

def test_missing_all_svix_headers_returns_400(make_request):
    req = make_request(method="POST", body=_USER_CREATED_EVENT)
    with patch.dict(os.environ, ENV):
        resp = clerk_webhook_core(req)
    assert resp.status_code == 400


def test_missing_svix_id_returns_400(make_request):
    headers = _svix_headers()
    del headers["svix-id"]
    req = make_request(method="POST", body=_USER_CREATED_EVENT, headers=headers)
    with patch.dict(os.environ, ENV):
        resp = clerk_webhook_core(req)
    assert resp.status_code == 400


def test_missing_svix_signature_returns_400(make_request):
    headers = _svix_headers()
    del headers["svix-signature"]
    req = make_request(method="POST", body=_USER_CREATED_EVENT, headers=headers)
    with patch.dict(os.environ, ENV):
        resp = clerk_webhook_core(req)
    assert resp.status_code == 400


# ── Signature verification ────────────────────────────────────────────────────

def test_invalid_signature_returns_400(make_request):
    """Bad signature must be rejected even with all headers present."""
    headers = _svix_headers(signature="v1,invalidsignature")
    req = make_request(method="POST", body=_USER_CREATED_EVENT, headers=headers)
    with patch.dict(os.environ, ENV):
        resp = clerk_webhook_core(req)
    # The Svix library raises WebhookVerificationError → our handler returns 400
    assert resp.status_code == 400


def test_no_webhook_secret_configured_returns_500(make_request):
    """Missing secret is a server-side misconfiguration, not a bad request."""
    env_without_secret = {k: v for k, v in ENV.items() if k != "CLERK_WEBHOOK_SECRET"}
    headers = _svix_headers()
    req = make_request(method="POST", body=_USER_CREATED_EVENT, headers=headers)
    with patch.dict(os.environ, env_without_secret, clear=False), \
         patch.dict(os.environ, {"CLERK_WEBHOOK_SECRET": ""}, clear=False):
        resp = clerk_webhook_core(req)
    assert resp.status_code == 500


# ── Event handling (signature bypassed via Webhook.verify mock) ───────────────

def _run_with_mocked_verify(make_request, mock_conn, event, env=None):
    """
    Run clerk_webhook_core with Webhook.verify patched to return `event` directly,
    so we can test DB logic without valid Svix signatures.
    """
    conn, cur = mock_conn
    cur.rowcount = 0  # default: UPDATE touches no rows → INSERT path

    headers = _svix_headers()
    req = make_request(method="POST", body=event, headers=headers)

    _env = {**(env or ENV)}

    with patch.dict(os.environ, _env), \
         patch("blueprints.clerk_webhook.Webhook") as MockWebhook, \
         patch("psycopg.connect", return_value=conn), \
         patch("blueprints.clerk_webhook.send_new_signup_notification"), \
         patch("blueprints.clerk_webhook.try_grant_founding_promo"), \
         patch("blueprints.clerk_webhook.try_grant_trial", return_value=False):

        mock_wh = MagicMock()
        MockWebhook.return_value = mock_wh
        mock_wh.verify.return_value = event

        resp = clerk_webhook_core(req)

    return resp, cur


def test_user_created_upserts_db_row(make_request, mock_conn):
    resp, cur = _run_with_mocked_verify(make_request, mock_conn, _USER_CREATED_EVENT)
    assert resp.status_code == 200
    # At least one DB execute should be the upsert INSERT/UPDATE
    executed_sql = " ".join(str(c) for c in cur.execute.call_args_list)
    assert "users" in executed_sql.lower()


def test_user_created_without_email_returns_200_and_skips_db(make_request, mock_conn):
    """If Clerk sends a user.created with no email, we log and skip — no DB call."""
    event = {
        "type": "user.created",
        "data": {
            "id": "user_no_email",
            "email_addresses": [],
            "primary_email_address_id": None,
            "first_name": "No",
            "last_name": "Email",
            "unsafe_metadata": {},
        },
    }
    resp, cur = _run_with_mocked_verify(make_request, mock_conn, event)
    assert resp.status_code == 200
    # No DB execute calls — we returned early
    assert not cur.execute.called


def test_user_deleted_executes_delete(make_request, mock_conn):
    resp, cur = _run_with_mocked_verify(make_request, mock_conn, _USER_DELETED_EVENT)
    assert resp.status_code == 200
    delete_calls = [
        c for c in cur.execute.call_args_list
        if "DELETE FROM users" in str(c)
    ]
    assert len(delete_calls) == 1


def test_user_deleted_without_id_returns_400(make_request, mock_conn):
    event = {"type": "user.deleted", "data": {}}  # no id
    resp, cur = _run_with_mocked_verify(make_request, mock_conn, event)
    assert resp.status_code == 400


def test_admin_email_user_created_grants_barrister(make_request, mock_conn):
    """User whose email matches ADMIN_EMAILS should get barrister tier set."""
    event = {
        "type": "user.created",
        "data": {
            "id": "user_admin_001",
            "email_addresses": [{"id": "ea_1", "email_address": "admin@example.com"}],
            "primary_email_address_id": "ea_1",
            "first_name": "Admin",
            "last_name": "User",
            "unsafe_metadata": {},
        },
    }
    resp, cur = _run_with_mocked_verify(make_request, mock_conn, event)
    assert resp.status_code == 200
    # One of the execute calls should set subscription_tier = 'barrister'
    admin_tier_calls = [
        c for c in cur.execute.call_args_list
        if "barrister" in str(c)
    ]
    assert len(admin_tier_calls) >= 1
