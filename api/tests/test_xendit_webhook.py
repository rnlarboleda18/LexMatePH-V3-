"""Tests for POST /api/xendit-webhook (blueprints/xendit.py).

Covers:
- Invalid callback token → 401
- Missing callback token when token is configured → 401
- No token configured → accepts any request
- Duplicate event skipped (idempotency: rowcount=0 means ON CONFLICT fired)
- First event processed (rowcount=1)
- Every known event type dispatches to the correct handler
- Unhandled event type returns 200 without crashing
- Malformed JSON body returns 500
"""
import json
import pytest
from unittest.mock import patch, MagicMock, call
from contextlib import contextmanager, ExitStack
from tests.conftest import make_request, parse_response, make_db, MockCursor, MockConnection

VALID_TOKEN = "test-webhook-token-xyz"


def _make_webhook_request(body: dict, token: str | None = VALID_TOKEN):
    headers = {}
    if token is not None:
        headers["x-callback-token"] = token
    return make_request("POST", body=body, headers=headers)


def _make_idempotency_db(rowcount: int) -> MockConnection:
    cur = MockCursor()
    cur.rowcount = rowcount
    conn = MockConnection(cursor=cur)

    @contextmanager
    def _txn():
        yield

    conn.transaction = _txn
    return conn


def _call(req, db_conn=None, token: str = VALID_TOKEN, rowcount: int = 1):
    from blueprints.xendit import xendit_webhook
    if db_conn is None:
        db_conn = _make_idempotency_db(rowcount)
    with patch("blueprints.xendit._get_db", return_value=db_conn), \
         patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", token):
        return xendit_webhook(req)


# ── Token verification ────────────────────────────────────────────────────────

def test_wrong_token_returns_401():
    req = _make_webhook_request({"event": "payment.succeeded", "data": {}}, token="wrong")
    resp = _call(req)
    assert resp.status_code == 401


def test_missing_token_returns_401():
    req = _make_webhook_request({"event": "payment.succeeded", "data": {}}, token=None)
    resp = _call(req)
    assert resp.status_code == 401


def test_correct_token_returns_200():
    req = _make_webhook_request({"event": "unknown.event", "data": {}})
    resp = _call(req)
    assert resp.status_code == 200


def test_no_token_configured_accepts_any_request():
    req = make_request("POST", body={"event": "test.event", "data": {}})
    resp = _call(req, token="")  # empty string = no token configured
    assert resp.status_code == 200


# ── Idempotency ───────────────────────────────────────────────────────────────

def test_duplicate_event_skips_handler():
    """rowcount=0 means ON CONFLICT DO NOTHING fired → duplicate, skip processing."""
    payload = {"event": "payment_session.completed", "data": {"id": "evt-dup-123"}}
    req = _make_webhook_request(payload)

    with patch("blueprints.xendit._handle_payment_succeeded") as mock_handler, \
         patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", VALID_TOKEN):
        db = _make_idempotency_db(rowcount=0)
        with patch("blueprints.xendit._get_db", return_value=db):
            from blueprints.xendit import xendit_webhook
            resp = xendit_webhook(req)

    assert resp.status_code == 200
    mock_handler.assert_not_called()


def test_new_event_calls_handler():
    """rowcount=1 means new event inserted → handler must be called."""
    payload = {"event": "payment_session.completed", "data": {"id": "evt-new-456"}}
    req = _make_webhook_request(payload)

    with patch("blueprints.xendit._handle_payment_succeeded") as mock_handler, \
         patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", VALID_TOKEN):
        db = _make_idempotency_db(rowcount=1)
        with patch("blueprints.xendit._get_db", return_value=db):
            from blueprints.xendit import xendit_webhook
            resp = xendit_webhook(req)

    assert resp.status_code == 200
    mock_handler.assert_called_once()


# ── Event dispatch ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("event_type,handler_name", [
    ("payment_session.completed",   "_handle_payment_succeeded"),
    ("payment.capture",             "_handle_payment_succeeded"),
    ("payment.succeeded",           "_handle_payment_succeeded"),
    ("payment_token.activation",    "_handle_payment_token_activated"),
    ("payment_token.activated",     "_handle_payment_token_activated"),
    ("recurring.plan.activated",    "_handle_plan_activated"),
    ("recurring_plan.activated",    "_handle_plan_activated"),
    ("recurring.plan.inactivated",  "_handle_plan_inactivated"),
    ("recurring_plan.inactivated",  "_handle_plan_inactivated"),
    ("recurring.cycle.succeeded",   "_handle_cycle_succeeded"),
    ("recurring_cycle.succeeded",   "_handle_cycle_succeeded"),
    ("recurring.cycle.failed",      "_handle_cycle_failed"),
    ("recurring_cycle.failed",      "_handle_cycle_failed"),
    ("recurring.cycle.retrying",    "_handle_cycle_retrying"),
    ("recurring_cycle.retrying",    "_handle_cycle_retrying"),
])
def test_event_dispatched_to_correct_handler(event_type, handler_name):
    payload = {"event": event_type, "data": {"id": f"id-for-{event_type}"}}
    req = _make_webhook_request(payload)

    with patch(f"blueprints.xendit.{handler_name}") as mock_handler, \
         patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", VALID_TOKEN):
        db = _make_idempotency_db(rowcount=1)
        with patch("blueprints.xendit._get_db", return_value=db):
            from blueprints.xendit import xendit_webhook
            resp = xendit_webhook(req)

    assert resp.status_code == 200
    mock_handler.assert_called_once()


def test_unhandled_event_type_returns_200():
    payload = {"event": "some.future.event.type", "data": {"id": "future-999"}}
    req = _make_webhook_request(payload)
    resp = _call(req)
    assert resp.status_code == 200


# ── Error handling ────────────────────────────────────────────────────────────

def test_malformed_json_returns_500():
    req = make_request(
        "POST", body=b"{{not valid json}",
        headers={"x-callback-token": VALID_TOKEN},
    )
    with patch("blueprints.xendit.XENDIT_WEBHOOK_TOKEN", VALID_TOKEN):
        from blueprints.xendit import xendit_webhook
        resp = xendit_webhook(req)
    assert resp.status_code == 500
