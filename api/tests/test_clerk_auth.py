"""
Clerk JWT auth — critical paths:
  1. Missing / malformed Authorization header
  2. Expired token rejected
  3. Valid HS256 token accepted and sub returned
"""
import time
import os
from unittest.mock import patch

import jwt
import pytest

from utils.clerk_auth import get_authenticated_user_id, validate_clerk_token


def _make_req_with_header(make_request, header_value):
    return make_request(
        method="GET",
        headers={"Authorization": header_value},
    )


def _hs256_token(sub, secret, exp_delta=3600):
    payload = {
        "sub": sub,
        "exp": int(time.time()) + exp_delta,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


SECRET = "test_secret_key_for_unit_tests"


# ── Missing / malformed header ────────────────────────────────────────────────

def test_missing_auth_header_returns_error(make_request):
    req = make_request(method="GET")
    clerk_id, error = get_authenticated_user_id(req)
    assert clerk_id is None
    assert error is not None


def test_empty_auth_header_returns_error(make_request):
    req = _make_req_with_header(make_request, "")
    clerk_id, error = get_authenticated_user_id(req)
    assert clerk_id is None
    assert error is not None


def test_missing_bearer_prefix_returns_error(make_request):
    req = _make_req_with_header(make_request, "sometoken_no_bearer_prefix")
    clerk_id, error = get_authenticated_user_id(req)
    assert clerk_id is None
    assert error is not None


def test_extra_spaces_in_header_returns_error(make_request):
    req = _make_req_with_header(make_request, "Bearer token extra_part")
    clerk_id, error = get_authenticated_user_id(req)
    assert clerk_id is None
    assert error is not None


# ── Token validation ──────────────────────────────────────────────────────────

def test_expired_hs256_token_returns_error():
    """A token whose exp is in the past must be rejected."""
    token = _hs256_token("user_expired", SECRET, exp_delta=-60)
    with patch("utils.clerk_auth.CLERK_SECRET_KEY", SECRET):
        clerk_id, error = validate_clerk_token(token)
    assert clerk_id is None
    assert error is not None


def test_valid_hs256_token_returns_sub():
    """A fresh signed HS256 token must return the sub claim."""
    token = _hs256_token("user_test_123", SECRET)
    with patch("utils.clerk_auth.CLERK_SECRET_KEY", SECRET):
        clerk_id, error = validate_clerk_token(token)
    assert error is None
    assert clerk_id == "user_test_123"


def test_empty_token_returns_error():
    clerk_id, error = validate_clerk_token("")
    assert clerk_id is None
    assert error is not None


def test_malformed_token_returns_error():
    clerk_id, error = validate_clerk_token("not.a.jwt")
    assert clerk_id is None
    assert error is not None


def test_valid_token_via_request(make_request):
    """End-to-end: valid Bearer token in request header returns clerk_id."""
    token = _hs256_token("user_e2e_456", SECRET)
    req = _make_req_with_header(make_request, f"Bearer {token}")
    with patch("utils.clerk_auth.CLERK_SECRET_KEY", SECRET):
        clerk_id, error = get_authenticated_user_id(req)
    assert error is None
    assert clerk_id == "user_e2e_456"
