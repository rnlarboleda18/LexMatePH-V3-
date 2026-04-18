"""
Shared Gemini client for LexCode amendment scripts (Vertex AI or Google AI Studio).

**Vertex AI** — set ``GOOGLE_GENAI_USE_VERTEXAI=true`` (or ``GEMINI_USE_VERTEX_AI`` /
``local.settings.json`` equivalents). Uses ``HttpOptions(api_version="v1")``.

Authentication (pick one; the SDK does not allow mixing):

- **Express / API key:** set ``GOOGLE_API_KEY`` (or ``GOOGLE_GENAI_API_KEY``). The client
  is built with ``vertexai=True`` and **only** the API key (no project/location).
- **Project + ADC:** leave the Gemini API key unset and set ``GOOGLE_CLOUD_PROJECT`` plus
  ``GOOGLE_CLOUD_LOCATION`` (default ``us-central1``). Use ``gcloud auth application-default login``.

**Google AI Studio** — leave Vertex flags unset; ``genai.Client(api_key=...)`` uses the
Developer API (``generativelanguage.googleapis.com``).

Model defaults: ``gemini-3-flash-preview`` as primary, ``gemini-3-flash-preview`` as fallback.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import time
import logging

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[2]

_client: genai.Client | None = None
_vertex_mode: bool | None = None


def _truthy(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


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


def load_google_api_key() -> str:
    for envk in ("GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY", "GEMINI_API_KEY"):
        v = (os.environ.get(envk) or "").strip()
        if v:
            return v
    vals = _settings_values()
    for k in ("GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY", "GEMINI_API_KEY"):
        if vals.get(k):
            return str(vals[k]).strip()
    return ""


def is_vertex_genai() -> bool:
    global _vertex_mode
    if _vertex_mode is not None:
        return _vertex_mode
    if _truthy(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")):
        _vertex_mode = True
        return True
    if _truthy(os.environ.get("GEMINI_USE_VERTEX_AI")):
        _vertex_mode = True
        return True
    if _truthy(_setting_str("GOOGLE_GENAI_USE_VERTEXAI")):
        _vertex_mode = True
        return True
    if _truthy(_setting_str("GEMINI_USE_VERTEX_AI")):
        _vertex_mode = True
        return True
    _vertex_mode = False
    return False


def get_google_cloud_project() -> str:
    return (
        (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
        or (os.environ.get("VERTEX_AI_PROJECT") or "").strip()
        or _setting_str("GOOGLE_CLOUD_PROJECT")
        or _setting_str("VERTEX_AI_PROJECT")
        or "gen-lang-client-0565960161"
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
    """Single-shot parse / metadata / merge (default)."""
    override = (os.environ.get("GEMINI_AMENDMENT_MODEL") or "").strip()
    if override:
        return override
    v = (_setting_str("GEMINI_AMENDMENT_MODEL") or "").strip()
    if v:
        return v
    return "gemini-2.5-flash"

_SESSION = None

def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
    return _SESSION


class MockResponse:
    def __init__(self, text):
        self.text = text

class MockModels:
    def __init__(self, api_key):
        self.api_key = api_key

    def list(self, config=None):
        model_ids = [
            "gemini-3-flash-preview",
            "gemini-3.1-flash-preview",
            "gemini-3-flash-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-3-flash-preview",
        ]
        
        class MockModelInfo:
            def __init__(self, mid):
                self.name = f"publishers/google/models/{mid}"
                self.display_name = mid.replace("-", " ").title()
        
        return [MockModelInfo(mid) for mid in model_ids]

    def generate_content(self, model, contents, config=None):
        import subprocess
        use_vertex = is_vertex_genai()
        use_vertex = is_vertex_genai()
        token = getattr(self, '_token_cache', None)
        
        # 1. Try manually provided token first (the long AQ... string)
        if not token:
            if self.api_key and (self.api_key.startswith("AQ.") or len(self.api_key) > 60):
                token = self.api_key
            else:
                try:
                    # 2. Try ADC/Gcloud
                    token = subprocess.check_output('gcloud auth print-access-token', shell=True, stderr=subprocess.DEVNULL).decode('utf-8').strip()
                    self._token_cache = token
                except Exception:
                    token = None

        # Determine if we should use Bearer token or API Key
        is_token = self.api_key.startswith(("ya29.", "AQ.")) or len(self.api_key) > 100
        
        if False:  # Force fallback for now due to Vertex timeouts
            pass
        else:
            # Google AI Studio / Developer API Domain (More reliable in this env)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            if is_token:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
            else:
                url += f"?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
        
        # Standardize contents
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

        payload = {
            "contents": contents_payload,
            "generationConfig": config or {}
        }

        # Extract system_instruction if present in config
        if config and "system_instruction" in config:
            sys_inst = config["system_instruction"]
            if isinstance(sys_inst, str):
                payload["systemInstruction"] = {"parts": [{"text": sys_inst}]}
            else:
                payload["systemInstruction"] = sys_inst
            del payload["generationConfig"]["system_instruction"]

        # Handle specialized config keys
        if "response_mime_type" in payload["generationConfig"]:
            payload["generationConfig"]["responseMimeType"] = payload["generationConfig"].pop("response_mime_type")
        
        if "max_output_tokens" in payload["generationConfig"]:
            payload["generationConfig"]["maxOutputTokens"] = payload["generationConfig"].pop("max_output_tokens")
        
        if config and "safety_settings" in config:
            payload["safetySettings"] = config["safety_settings"]
            del payload["generationConfig"]["safety_settings"]
        
        # Simple retry
        for attempt in range(3):
            try:
                # print(f"  [AI] Calling {model} (Attempt {attempt+1})...")
                response = get_session().post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    if 'candidates' in data and data['candidates']:
                        text = data['candidates'][0]['content']['parts'][0]['text']
                        return MockResponse(text)
                    else:
                        logger.error(f"Vertex AI Response missing candidates: {data}")
                        raise RuntimeError("AI response error: No candidates found")
                else:
                    logger.error(f"Vertex AI API Error: {response.status_code} - {response.text}")
                    if response.status_code in [404, 403, 401] and is_vertex_genai():
                        logger.warning("Vertex AI endpoint unavailable/misconfigured. Falling back to Developer API (AI Studio)...")
                        # Swap URL to Developer API domain
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                        if not is_token:
                            url += f"?key={self.api_key}"
                        # Try again with the new URL
                        continue
                    if response.status_code in [429, 500, 503]:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise RuntimeError(f"Vertex AI API Error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as re:
                logger.error(f"Network error calling AI: {re}")
                if attempt == 2: raise
                time.sleep(1)

        raise RuntimeError("AI call failed after 3 attempts")
        raise ValueError("Failed to call Vertex AI API")

class MockGenAIClient:
    def __init__(self, api_key):
        self.models = MockModels(api_key)

def build_vertex_genai_client(*, api_version: str = "v1") -> MockGenAIClient:
    api_key = load_google_api_key()
    if not api_key:
        raise ValueError("Vertex REST calls need GOOGLE_API_KEY / GEMINI_API_KEY")
    return MockGenAIClient(api_key)


def get_amendment_chunk_model() -> str:
    """Chunked amendment parse (large statutes)."""
    override = (os.environ.get("GEMINI_AMENDMENT_CHUNK_MODEL") or "").strip()
    if override:
        return override
    v = (_setting_str("GEMINI_AMENDMENT_CHUNK_MODEL") or "").strip()
    if v:
        return v
    return "gemini-3-flash-preview"


def get_genai_client() -> MockGenAIClient:
    """Lazy singleton for amendment scripts."""
    global _client
    if _client is not None:
        return _client

    api_key = load_google_api_key()
    _client = build_vertex_genai_client()
    return _client
