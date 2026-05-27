"""
Xendit webhook — critical paths:
  1. Token verification (auth gate)
  2. Idempotency guard (prevents duplicate tier grants)
  3. Event routing (correct handler is called)
"""
import json
import os
from unittest.mock import MagicMock, patch, call

import pytest

from blueprints.xendit import xendit_webhook


# ── Helpers ──────────────────────────────────────────────────────────────────

def _payment_event(evt_type="payment.succeeded", clerk_id="user_abc123"):
    return {
        "event": evt_type,
        "data": {
            "id": "pay_test_001",
            "metadata": {"clerk_id": clerk_id, "plan_key": "amicus_monthly"},
            "customer_id": "cust_test_001",
        },
    }


def _make_webhook_request(make_request, body, token=None):
    headers = {}
    if token is not None:
        headers["x-callback-token"] = token
    return make_request(method="POST", body=body, headers=headers)


# ── Token verification ────────────────────────────────────────────────────────

def test_webhook_rejects_wrong_token(make_request):
    """Returns 401 when a webhook token is configured but caller sends the wrong one."""
    req = _make_webhook_request(make_request, _payment_event(), token="wrong_token")
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", "correct_token"):
        resp = xendit_webhook(req)
    assert resp.status_code == 401


def test_webhook_rejects_missing_token(make_request):
    """Returns 401 when a webhook token is configured but caller sends none."""
    req = _make_webhook_request(make_request, _payment_event(), token=None)
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", "correct_token"):
        resp = xendit_webhook(req)
    assert resp.status_code == 401


def test_webhook_rejects_when_no_token_configured(make_request):
    """When XENDIT_WEBHOOK_TOKEN is empty the webhook rejects all calls (secure default)."""
    req = _make_webhook_request(make_request, _payment_event(), token=None)
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", ""):
        resp = xendit_webhook(req)
    assert resp.status_code == 403


# ── Idempotency guard ─────────────────────────────────────────────────────────

_TEST_TOKEN = "test_webhook_secret"


def test_webhook_duplicate_event_returns_ok_without_processing(make_request, mock_conn):
    """
    When the same event id is received twice the idempotency INSERT returns
    rowcount=0 (ON CONFLICT DO NOTHING).  The webhook must short-circuit and
    return 200 without calling any payment handler.
    """
    conn, cur = mock_conn
    cur.rowcount = 0  # already seen

    req = _make_webhook_request(make_request, _payment_event(), token=_TEST_TOKEN)
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", _TEST_TOKEN), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit._handle_payment_succeeded") as mock_handler:
        resp = xendit_webhook(req)

    assert resp.status_code == 200
    mock_handler.assert_not_called()


def test_webhook_new_event_calls_payment_handler(make_request, mock_conn):
    """
    When the idempotency INSERT succeeds (rowcount=1) the payment handler
    must be called for payment.succeeded events.
    """
    conn, cur = mock_conn
    cur.rowcount = 1  # first time seen

    event = _payment_event("payment.succeeded")
    req = _make_webhook_request(make_request, event, token=_TEST_TOKEN)
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", _TEST_TOKEN), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit._handle_payment_succeeded") as mock_handler:
        resp = xendit_webhook(req)

    assert resp.status_code == 200
    mock_handler.assert_called_once_with(event["data"])


def test_webhook_payment_session_completed_calls_handler(make_request, mock_conn):
    """payment_session.completed must also route to _handle_payment_succeeded."""
    conn, cur = mock_conn
    cur.rowcount = 1

    event = _payment_event("payment_session.completed")
    req = _make_webhook_request(make_request, event, token=_TEST_TOKEN)
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", _TEST_TOKEN), \
         patch("blueprints.xendit._get_db", return_value=conn), \
         patch("blueprints.xendit._handle_payment_succeeded") as mock_handler:
        xendit_webhook(req)

    mock_handler.assert_called_once_with(event["data"])


def test_webhook_unknown_event_returns_200_without_error(make_request, mock_conn):
    """Unrecognised event types are silently ignored — no 500."""
    conn, cur = mock_conn
    cur.rowcount = 1

    event = {"event": "some.future.event", "data": {"id": "x_001"}}
    req = _make_webhook_request(make_request, event, token=_TEST_TOKEN)
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", _TEST_TOKEN), \
         patch("blueprints.xendit._get_db", return_value=conn):
        resp = xendit_webhook(req)

    assert resp.status_code == 200
