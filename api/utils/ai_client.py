"""
ai_client.py — Google AI Studio REST client (API key only).

Auth: GOOGLE_API_KEY (or GEMINI_API_KEY) from api/local.settings.json → Values.
Model: GEMINI_VERTEX_MODEL env var (reused for naming compat), default gemini-3-flash-preview.
Fallback model: GEMINI_DIGEST_FALLBACK_MODEL, default gemini-2.5-flash.
"""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union

import requests

logger = logging.getLogger(__name__)

_AI_STUDIO_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

DEFAULT_MODEL    = os.environ.get("GEMINI_VERTEX_MODEL") or os.environ.get("GEMINI_DIGEST_MODEL") or "gemini-3-flash-preview"
FALLBACK_MODEL   = os.environ.get("GEMINI_DIGEST_FALLBACK_MODEL") or "gemini-2.5-flash"

_http_session: Optional[requests.Session] = None


def _session() -> requests.Session:
    global _http_session
    if _http_session is None:
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json", "Connection": "keep-alive"})
        _http_session = s
    return _http_session


def _api_key() -> str:
    for var in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY"):
        v = (os.environ.get(var) or "").strip()
        if v:
            return v
    raise ValueError(
        "No Google AI Studio API key found. "
        "Set GOOGLE_API_KEY in api/local.settings.json → Values."
    )


def call_vertex_ai(
    prompt: Union[str, List[Dict[str, Any]]],
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    response_mime_type: str = "text/plain",
    model: str = DEFAULT_MODEL,
    retries: int = 3,
    backoff_factor: float = 1.5,
) -> str:
    """Generate content via Google AI Studio REST API (API key auth).

    Function name kept as call_vertex_ai for backward compatibility with all callers.
    """
    key = _api_key()
    if isinstance(prompt, str):
        contents: List[Dict[str, Any]] = [{"role": "user", "parts": [{"text": prompt}]}]
    else:
        contents = prompt

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": response_mime_type,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    url = f"{_AI_STUDIO_BASE}/{model}:generateContent?key={key}"
    session = _session()
    last_error: Optional[str] = None

    for attempt in range(retries):
        try:
            resp = session.post(url, data=json.dumps(payload), timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    raise ValueError(f"Unexpected AI Studio response structure: {data}")

            if resp.status_code in (429, 500, 502, 503, 504):
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                wait = backoff_factor ** attempt
                logger.warning("AI Studio retry %s/%s in %ss: %s", attempt + 1, retries, wait, last_error)
                time.sleep(wait)
                continue

            raise ValueError(f"AI Studio error {resp.status_code}: {resp.text[:300]}")

        except requests.RequestException as e:
            last_error = str(e)
            time.sleep(backoff_factor ** attempt)

    raise ValueError(f"AI Studio failed after {retries} attempts. Last: {last_error}")


def call_vertex_ai_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """JSON-mode wrapper around call_vertex_ai."""
    text = call_vertex_ai(
        prompt=prompt,
        system_instruction=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
        response_mime_type="application/json",
        model=model,
    )
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:-3].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:-3].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("AI Studio returned invalid JSON: %s", text)
        raise ValueError(f"AI Studio returned invalid JSON: {e}") from e
