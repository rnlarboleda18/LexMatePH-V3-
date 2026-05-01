"""
Shared Google GenAI client for codal linker scripts — AI Studio API key only.

Auth: GOOGLE_API_KEY (or GEMINI_API_KEY) from api/local.settings.json → Values.

Optional env vars:
  GEMINI_LINKER_MODEL           — override model id (default: gemini-3-flash-preview)
  GEMINI_DIGEST_FALLBACK_MODEL  — fallback model (default: gemini-2.5-flash)
  GEMINI_LINKER_HTTP_TIMEOUT_MS — per-request timeout in ms (default 300000)

Probe availability::

    python scripts/linker_genai_client.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_LINKER_MODEL  = "gemini-3-flash-preview"
FALLBACK_LINKER_MODEL = "gemini-2.5-flash"

_genai_client = None


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
    for k, v in vals.items():
        if k not in os.environ or not str(os.environ.get(k, "")).strip():
            os.environ[str(k)] = str(v) if v is not None else ""


def _resolve_api_key() -> str:
    """Return the first non-empty Google AI Studio API key found in the env."""
    for var in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY"):
        val = (os.environ.get(var) or "").strip()
        if val:
            return val
    return ""


def get_linker_genai_client():
    """Return a shared ``google.genai.Client`` using Google AI Studio API key."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    merge_local_settings_into_env()

    # Force AI Studio mode — clear any Vertex-routing env vars that
    # the google.genai SDK picks up automatically.
    for _v in ("GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT",
               "GOOGLE_CLOUD_LOCATION", "VERTEX_AI_PROJECT", "VERTEX_AI_LOCATION"):
        os.environ.pop(_v, None)

    from google import genai
    from google.genai import types as genai_types

    raw_to = (os.environ.get("GEMINI_LINKER_HTTP_TIMEOUT_MS") or "").strip()
    try:
        timeout_ms = int(raw_to) if raw_to else 300_000
    except ValueError:
        timeout_ms = 300_000
    timeout_ms = max(timeout_ms, 10_000)

    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError(
            "Codal linker requires GOOGLE_API_KEY (Google AI Studio).\n"
            "Add it to api/local.settings.json → Values."
        )

    _genai_client = genai.Client(
        api_key=api_key,
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


def is_linker_configured() -> bool:
    """Return True if GOOGLE_API_KEY is available."""
    merge_local_settings_into_env()
    return bool(_resolve_api_key())


def probe_linker() -> None:
    """One minimal generateContent call to verify the API key and model."""
    merge_local_settings_into_env()
    client = get_linker_genai_client()
    model  = get_linker_model_name()
    print(f"Linker probe: mode='AI Studio (API key)'  model={model!r}")
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
