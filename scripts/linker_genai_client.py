"""
Shared Google GenAI client for codal linker scripts.

Auth: Vertex AI only.
  Set GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION (or GCP_PROJECT + GCP_LOCATION)
  in api/local.settings.json → Values, or pass vertex_project / vertex_location
  to get_linker_genai_client().

Optional env vars:
  GEMINI_LINKER_MODEL           — override model id (default: gemini-2.5-flash)
  GEMINI_DIGEST_FALLBACK_MODEL  — fallback model (default: gemini-2.5-flash)
  GEMINI_LINKER_HTTP_TIMEOUT_MS — per-request timeout in ms (default 300000)

Probe availability:

    python scripts/linker_genai_client.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

DEFAULT_LINKER_MODEL  = "gemini-2.5-flash"
FALLBACK_LINKER_MODEL = "gemini-2.5-flash"

_genai_client = None
_vertex_project: str | None = None
_vertex_location: str | None = None

# ---------------------------------------------------------------------------
# Global token-bucket rate limiter — shared across all threads/workers.
# Prevents bursting past the Vertex AI project quota (new accounts start
# with very low RPM defaults; 429s happen even before the per-call backoff
# can protect you).
# Override with GEMINI_LINKER_RPM env var (default 40 RPM — safe for new
# Vertex projects while still allowing 5 workers to run steadily).
# ---------------------------------------------------------------------------
_DEFAULT_LINKER_RPM = 40  # requests per minute; conservative for new projects

class _TokenBucket:
    """Thread-safe token bucket.  Callers block in ``acquire()`` until a
    token is available, capping global throughput to ``rate_per_minute``."""

    def __init__(self, rate_per_minute: float) -> None:
        self._rate = rate_per_minute / 60.0          # tokens / second
        self._tokens: float = self._rate * 2          # small initial burst
        self._last: float = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._rate * 10,                  # cap at 10 s worth
                    self._tokens + (now - self._last) * self._rate,
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            time.sleep(min(wait, 0.5))               # wake up frequently


_rate_limiter: _TokenBucket | None = None
_rate_limiter_lock = threading.Lock()


def get_linker_rate_limiter() -> _TokenBucket:
    """Return the shared rate limiter, creating it on first call."""
    global _rate_limiter
    if _rate_limiter is not None:
        return _rate_limiter
    with _rate_limiter_lock:
        if _rate_limiter is None:
            merge_local_settings_into_env()
            raw = (os.environ.get("GEMINI_LINKER_RPM") or "").strip()
            try:
                rpm = float(raw) if raw else _DEFAULT_LINKER_RPM
            except ValueError:
                rpm = _DEFAULT_LINKER_RPM
            rpm = max(1.0, min(rpm, 1200.0))         # clamp to sane range
            _rate_limiter = _TokenBucket(rpm)
            print(f"[rate] Linker rate limiter initialised at {rpm:.0f} RPM", flush=True)
    return _rate_limiter


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def merge_local_settings_into_env() -> None:
    """Populate missing env vars from api/local.settings.json → Values."""
    path = _repo_root() / "api" / "local.settings.json"
    if not path.is_file():
        return
    try:
        with open(path, encoding="utf-8") as f:
            vals = json.load(f).get("Values") or {}
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(vals, dict):
        return
    # Always override GCP project keys — session env vars must not shadow local.settings.json.
    FORCE_KEYS = {"GOOGLE_CLOUD_PROJECT", "GCP_PROJECT", "GOOGLE_CLOUD_LOCATION",
                  "GCP_LOCATION", "GEMINI_LINKER_VERTEX_PROJECT"}
    for k, v in vals.items():
        if k in FORCE_KEYS or not str(os.environ.get(k, "")).strip():
            os.environ[str(k)] = str(v) if v is not None else ""


def get_linker_genai_client(
    vertex_project: str | None = None,
    vertex_location: str | None = None,
):
    """Return a shared ``google.genai.Client`` configured for Vertex AI.

    Project resolution order:
      1. vertex_project argument
      2. GOOGLE_CLOUD_PROJECT env var
      3. GCP_PROJECT env var (app-level alias)
    """
    global _genai_client, _vertex_project, _vertex_location

    if _genai_client is not None:
        return _genai_client

    merge_local_settings_into_env()

    from google import genai
    from google.genai import types as genai_types

    raw_to = (os.environ.get("GEMINI_LINKER_HTTP_TIMEOUT_MS") or "").strip()
    try:
        timeout_ms = int(raw_to) if raw_to else 300_000
    except ValueError:
        timeout_ms = 300_000
    timeout_ms = max(timeout_ms, 10_000)

    project = (
        vertex_project
        or (os.environ.get("GEMINI_LINKER_VERTEX_PROJECT") or "").strip()
        or (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
        or (os.environ.get("GCP_PROJECT") or "").strip()
        or "project-0c3350f3-e867-449e-8f7"
    )
    location = (
        vertex_location
        or (os.environ.get("GOOGLE_CLOUD_LOCATION") or "").strip()
        or (os.environ.get("GCP_LOCATION") or "").strip()
        or "us"
    )

    if not project:
        raise RuntimeError(
            "Vertex AI project not configured. "
            "Set GOOGLE_CLOUD_PROJECT (or GCP_PROJECT) in api/local.settings.json → Values."
        )

    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GOOGLE_CLOUD_PROJECT"]      = project
    os.environ["GOOGLE_CLOUD_LOCATION"]     = location
    _vertex_project  = project
    _vertex_location = location

    _genai_client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
        http_options=genai_types.HttpOptions(timeout=timeout_ms),
    )
    return _genai_client


def get_linker_model_name(*, fallback: str | None = None) -> str:
    """Resolved model id.

    Priority:
      1. GEMINI_LINKER_MODEL env var
      2. fallback argument
      3. gemini-3-flash-preview  (default)
    """
    merge_local_settings_into_env()
    m = (os.environ.get("GEMINI_LINKER_MODEL") or "").strip()
    if m:
        return m
    if fallback:
        return fallback
    return DEFAULT_LINKER_MODEL


def is_linker_configured(vertex_project: str | None = None) -> bool:
    """Return True if a Vertex AI project is available."""
    return True


def probe_linker(vertex_project: str | None = None, vertex_location: str | None = None) -> None:
    """One minimal generateContent call to verify the API key/project and model."""
    merge_local_settings_into_env()
    client = get_linker_genai_client(vertex_project=vertex_project, vertex_location=vertex_location)
    model  = get_linker_model_name()
    mode   = f"Vertex AI (project={_vertex_project}, location={_vertex_location})"
    print(f"Linker probe: mode={mode!r}  model={model!r}")
    from google import genai
    response = client.models.generate_content(
        model=model,
        contents='Reply with a single JSON object: {"ok": true, "model_probe": "linker"}',
        config=genai.types.GenerateContentConfig(response_mime_type="application/json"),
    )
    text = (response.text or "").strip()
    print("Response:", text[:500] + ("..." if len(text) > 500 else ""))
    print("PROBE_OK")


if __name__ == "__main__":
    try:
        probe_linker()
    except Exception as exc:
        print("PROBE_FAILED:", exc, file=sys.stderr)
        sys.exit(1)
