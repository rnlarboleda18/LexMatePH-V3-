"""
Thin Xendit REST client.

Single source of truth for:
  - XENDIT_BASE_URL constant
  - _xendit_headers()  — build Auth + Content-Type headers
  - _with_retry()      — exponential backoff for transient errors
  - xendit_post/get/delete — typed wrappers that callers use instead of
    inline requests.post / requests.get / requests.delete calls.

All wrappers return the raw requests.Response so that callers can still
inspect status_code and call .json() themselves — no behaviour changes.

Usage:
    from utils.xendit_client import xendit_post, xendit_get, xendit_delete

    resp = xendit_post("/sessions", payload)           # retried by default
    resp = xendit_post("/recurring/plans", payload,    # non-idempotent: no retry
                       api_version="2026-01-01",
                       retry=False)
    resp = xendit_get("/recurring/plans/rp_abc",
                      api_version="2026-01-01")
    resp = xendit_delete("/recurring/plans/rp_abc",
                         api_version="2026-01-01")
"""
import base64
import logging
import os
import time

import requests

# ── Constants ─────────────────────────────────────────────────────────────────

XENDIT_BASE_URL = "https://api.xendit.co"

_RETRYABLE_STATUSES = (429, 500, 502, 503)


# ── Core helpers ──────────────────────────────────────────────────────────────

def _xendit_headers(api_version: str | None = None) -> dict:
    """Return auth + content-type headers for Xendit REST calls.

    XENDIT_API_KEY is read from os.environ at call time (not from config) so
    that hot app-setting updates are picked up without a cold start.
    Raises RuntimeError if the key is absent (deployment misconfiguration).
    """
    key = (os.environ.get("XENDIT_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("XENDIT_API_KEY is not set")
    encoded = base64.b64encode(f"{key}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
    }
    if api_version:
        headers["api-version"] = api_version
    return headers


def _with_retry(fn, max_attempts: int = 3, base_delay: float = 1.0):
    """Call fn() (which must return a requests.Response) with exponential backoff.

    Retries on network errors and on 429 / 5xx responses.
    """
    last_exc: Exception = RuntimeError("No attempt made")
    for attempt in range(max_attempts):
        try:
            resp = fn()
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logging.warning(
                    "Xendit network error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, max_attempts, exc, delay,
                )
                time.sleep(delay)
            continue
        if resp.status_code in _RETRYABLE_STATUSES and attempt < max_attempts - 1:
            delay = base_delay * (2 ** attempt)
            logging.warning(
                "Xendit HTTP %s (attempt %d/%d) — retrying in %.1fs",
                resp.status_code, attempt + 1, max_attempts, delay,
            )
            last_exc = RuntimeError(f"Xendit HTTP {resp.status_code}")
            time.sleep(delay)
            continue
        return resp
    raise last_exc


# ── Typed wrappers ─────────────────────────────────────────────────────────────

def xendit_post(
    path: str,
    body: dict,
    *,
    api_version: str | None = None,
    timeout: int = 20,
    retry: bool = True,
) -> requests.Response:
    """POST to Xendit API.

    Args:
        path: URL path relative to XENDIT_BASE_URL (e.g. "/sessions").
        body: JSON-serialisable request payload.
        api_version: If set, adds the ``api-version`` header.
        timeout: Request timeout in seconds (default 20).
        retry: When True (default) applies exponential backoff on transient
               errors. Set to False for non-idempotent calls such as creating
               a recurring plan where a retry could produce a duplicate.

    Returns:
        The raw requests.Response — callers check status_code themselves.
    """
    def _call():
        return requests.post(
            f"{XENDIT_BASE_URL}{path}",
            headers=_xendit_headers(api_version),
            json=body,
            timeout=timeout,
        )
    return _with_retry(_call) if retry else _call()


def xendit_get(
    path: str,
    *,
    api_version: str | None = None,
    timeout: int = 15,
    retry: bool = True,
) -> requests.Response:
    """GET from Xendit API."""
    def _call():
        return requests.get(
            f"{XENDIT_BASE_URL}{path}",
            headers=_xendit_headers(api_version),
            timeout=timeout,
        )
    return _with_retry(_call) if retry else _call()


def xendit_delete(
    path: str,
    *,
    api_version: str | None = None,
    timeout: int = 15,
    retry: bool = True,
) -> requests.Response:
    """DELETE via Xendit API."""
    def _call():
        return requests.delete(
            f"{XENDIT_BASE_URL}{path}",
            headers=_xendit_headers(api_version),
            timeout=timeout,
        )
    return _with_retry(_call) if retry else _call()
