"""
Shared Gemini client for LexCode amendment scripts — Vertex AI ONLY.

Authentication (Application Default Credentials):
  1. Preferred: ``google-auth`` library picks up ADC automatically
     (service account JSON via GOOGLE_APPLICATION_CREDENTIALS, or
     ``gcloud auth application-default login`` on a developer workstation).
  2. Fallback: ``gcloud auth print-access-token`` subprocess (dev only).

Endpoint used:
  https://{location}-aiplatform.googleapis.com/v1/projects/{project}
    /locations/{location}/publishers/google/models/{model}:generateContent

Required settings (api/local.settings.json or environment):
  GOOGLE_CLOUD_PROJECT   — your GCP project ID
  GOOGLE_CLOUD_LOCATION  — e.g. us-central1 (default)

Optional override:
  GEMINI_AMENDMENT_MODEL — primary model (default: gemini-2.5-pro)
  GEMINI_AMENDMENT_CHUNK_MODEL — chunked / large-doc parser (default: gemini-2.5-flash)

Google AI Studio / API keys are NOT used and NOT supported here.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Documented max output tokens for Gemini 2.5 on Vertex (e.g. 2.5 Pro); the API clamps per model if lower.
VERTEX_GEMINI_MAX_OUTPUT_TOKENS = 65536

_REPO = Path(__file__).resolve().parents[2]

# Module-level singletons
_client: "VertexGenAIClient | None" = None
_access_token_cache: str | None = None
_token_expiry: float = 0.0


# ── Settings helpers ──────────────────────────────────────────────────────────

def _settings_values() -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for p in (_REPO / "api" / "local.settings.json", _REPO / "local.settings.json"):
        if not p.is_file():
            continue
        try:
            with open(p, encoding="utf-8") as f:
                vals = json.load(f).get("Values") or {}
            if isinstance(vals, dict):
                merged.update(vals)
        except OSError:
            continue
    return merged


def _setting_str(name: str) -> str:
    v = (os.environ.get(name) or "").strip()
    if v:
        return v
    vals = _settings_values()
    x = vals.get(name)
    return str(x).strip() if x is not None else ""


def get_google_cloud_project() -> str:
    return (
        (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
        or (os.environ.get("VERTEX_AI_PROJECT") or "").strip()
        or _setting_str("GOOGLE_CLOUD_PROJECT")
        or _setting_str("VERTEX_AI_PROJECT")
    )


def get_google_cloud_location() -> str:
    return (
        (os.environ.get("GOOGLE_CLOUD_LOCATION") or "").strip()
        or (os.environ.get("VERTEX_AI_LOCATION") or "").strip()
        or _setting_str("GOOGLE_CLOUD_LOCATION")
        or _setting_str("VERTEX_AI_LOCATION")
        or "us-central1"
    )


def get_amendment_primary_model() -> str:
    override = (os.environ.get("GEMINI_AMENDMENT_MODEL") or "").strip()
    if override:
        return override
    v = (_setting_str("GEMINI_AMENDMENT_MODEL") or "").strip()
    if v:
        return v
    return "gemini-2.5-pro"


def get_amendment_chunk_model() -> str:
    override = (os.environ.get("GEMINI_AMENDMENT_CHUNK_MODEL") or "").strip()
    if override:
        return override
    v = (_setting_str("GEMINI_AMENDMENT_CHUNK_MODEL") or "").strip()
    if v:
        return v
    return "gemini-2.5-flash"


# ── OAuth2 token acquisition ──────────────────────────────────────────────────

def _get_access_token() -> str:
    """Return a valid OAuth2 Bearer token for Vertex AI.

    Priority:
      0. VERTEX_AI_ACCESS_TOKEN environment variable (direct override).
      1. google-auth ADC (recommended — works with service accounts and
         ``gcloud auth application-default login``).
      2. ``gcloud auth print-access-token`` subprocess (dev fallback).
    """
    global _access_token_cache, _token_expiry

    # 0. Direct Override (Highest Priority)
    override = os.environ.get("VERTEX_AI_ACCESS_TOKEN")
    if override:
        return override

    # Return cached token if still valid (5-minute buffer)
    if _access_token_cache and time.time() < _token_expiry - 300:
        return _access_token_cache

    # 1. google-auth ADC
    try:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        token = credentials.token
        if token:
            _access_token_cache = token
            # google-auth expiry is a datetime; convert to epoch float
            if credentials.expiry:
                import datetime
                expiry_dt = credentials.expiry
                if expiry_dt.tzinfo is None:
                    import calendar
                    _token_expiry = calendar.timegm(expiry_dt.timetuple())
                else:
                    _token_expiry = expiry_dt.timestamp()
            else:
                _token_expiry = time.time() + 3600
            logger.debug("Vertex AI token obtained via google-auth ADC.")
            return token
    except ImportError:
        logger.warning("google-auth not installed; falling back to gcloud subprocess.")
    except Exception as e:
        logger.warning(f"google-auth ADC failed ({e}); falling back to gcloud subprocess.")

    # 2. gcloud subprocess
    try:
        token = subprocess.check_output(
            "gcloud auth print-access-token",
            shell=True,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if not token:
            raise RuntimeError("gcloud returned empty token.")
        _access_token_cache = token
        _token_expiry = time.time() + 3600  # gcloud tokens live ~1 hour
        logger.debug("Vertex AI token obtained via gcloud subprocess.")
        return token
    except Exception as e:
        raise RuntimeError(
            "Cannot obtain a Vertex AI OAuth2 token.\n"
            "Run: gcloud auth application-default login\n"
            f"Error: {e}"
        ) from e


# ── HTTP session ──────────────────────────────────────────────────────────────

_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
    return _SESSION


# ── Response wrapper ──────────────────────────────────────────────────────────

class MockResponse:
    def __init__(self, text: str):
        self.text = text


# ── Vertex AI model client ────────────────────────────────────────────────────

class VertexModels:
    """Thin REST wrapper around the Vertex AI generateContent API."""

    def generate_content(self, model: str, contents, config=None) -> MockResponse:
        project = get_google_cloud_project()
        location = get_google_cloud_location()

        if not project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is not set. "
                "Add it to api/local.settings.json or set as an environment variable."
            )

        url = (
            f"https://{location}-aiplatform.googleapis.com/v1"
            f"/projects/{project}/locations/{location}"
            f"/publishers/google/models/{model}:generateContent"
        )

        # ── Normalise contents ────────────────────────────────────────────
        if isinstance(contents, str):
            contents_payload = [{"role": "user", "parts": [{"text": contents}]}]
        elif isinstance(contents, list):
            contents_payload = []
            for item in contents:
                if isinstance(item, str):
                    contents_payload.append({"role": "user", "parts": [{"text": item}]})
                else:
                    contents_payload.append(item)
        else:
            contents_payload = contents

        # ── Build payload ─────────────────────────────────────────────────
        gen_config = dict(config) if config else {}

        # snake_case → camelCase for REST API
        if "response_mime_type" in gen_config:
            gen_config["responseMimeType"] = gen_config.pop("response_mime_type")
        if "max_output_tokens" in gen_config:
            gen_config.pop("max_output_tokens", None)
        gen_config["maxOutputTokens"] = VERTEX_GEMINI_MAX_OUTPUT_TOKENS

        payload: dict = {"contents": contents_payload, "generationConfig": gen_config}

        if "system_instruction" in gen_config:
            sys_inst = gen_config.pop("system_instruction")
            payload["systemInstruction"] = (
                {"parts": [{"text": sys_inst}]} if isinstance(sys_inst, str) else sys_inst
            )

        if "safety_settings" in gen_config:
            payload["safetySettings"] = gen_config.pop("safety_settings")

        # ── Call with retry ───────────────────────────────────────────────
        for attempt in range(3):
            token = _get_access_token()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
            try:
                resp = _get_session().post(url, headers=headers, json=payload, timeout=600)

                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return MockResponse(text)
                    except (KeyError, IndexError) as e:
                        raise RuntimeError(
                            f"Unexpected Vertex AI response shape: {data}"
                        ) from e

                elif resp.status_code == 401:
                    # Token may have expired; clear cache and retry once
                    global _access_token_cache
                    _access_token_cache = None
                    logger.warning("Vertex AI 401 — token refresh triggered.")
                    if attempt < 2:
                        continue
                    raise RuntimeError(
                        f"Vertex AI 401 after token refresh: {resp.text[:300]}"
                    )

                elif resp.status_code in (429, 500, 503):
                    logger.warning(
                        f"Vertex AI transient {resp.status_code}, retrying ({attempt+1}/3)..."
                    )
                    time.sleep(2 ** attempt)
                    continue

                else:
                    raise RuntimeError(
                        f"Vertex AI API error {resp.status_code}: {resp.text[:400]}"
                    )

            except requests.exceptions.RequestException as exc:
                logger.error(f"Network error calling Vertex AI: {exc}")
                if attempt == 2:
                    raise RuntimeError(
                        f"Vertex AI call failed after 3 attempts: {exc}"
                    ) from exc
                # Longer backoff for read timeouts / flaky TLS
                delay = 3 * (2**attempt)
                logger.warning(f"Retrying Vertex request in {delay}s ({attempt + 2}/3)...")
                time.sleep(delay)

        raise RuntimeError("Vertex AI call failed after 3 attempts.")


class VertexGenAIClient:
    def __init__(self):
        self.models = VertexModels()


# ── Public factory ────────────────────────────────────────────────────────────

def get_genai_client() -> VertexGenAIClient:
    """Return the shared Vertex AI client singleton."""
    global _client
    if _client is None:
        _client = VertexGenAIClient()
    return _client


def build_vertex_genai_client(**_kwargs) -> VertexGenAIClient:
    """Compatibility alias for older call sites."""
    return get_genai_client()
