"""Minimal Gemini calls via REST so we avoid the heavy google-generativeai / gRPC stack (SWA size limit)."""
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests

GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

_RETRYABLE_STATUSES = (429, 500, 502, 503)
_MAX_ATTEMPTS = 3
_BASE_DELAY = 1.0


def gemini_generate_text(
    model: str,
    prompt: str,
    *,
    response_mime_type: Optional[str] = None,
    generation_config: Optional[Dict[str, Any]] = None,
    timeout: int = 300,
) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    url = GEMINI_GENERATE_URL.format(model=model)
    body: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }
    gen_cfg: Dict[str, Any] = dict(generation_config or {})
    if response_mime_type:
        gen_cfg["responseMimeType"] = response_mime_type
    if gen_cfg:
        body["generationConfig"] = gen_cfg

    last_exc: Exception = RuntimeError("Gemini request failed before any attempt")

    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = requests.post(
                url,
                params={"key": api_key},
                json=body,
                timeout=timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            if attempt < _MAX_ATTEMPTS - 1:
                delay = _BASE_DELAY * (2 ** attempt)
                logging.warning(
                    "Gemini network error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, _MAX_ATTEMPTS, exc, delay,
                )
                time.sleep(delay)
            continue

        if resp.status_code in _RETRYABLE_STATUSES and attempt < _MAX_ATTEMPTS - 1:
            delay = _BASE_DELAY * (2 ** attempt)
            logging.warning(
                "Gemini HTTP %s (attempt %d/%d) — retrying in %.1fs",
                resp.status_code, attempt + 1, _MAX_ATTEMPTS, delay,
            )
            last_exc = RuntimeError(f"Gemini HTTP {resp.status_code}")
            time.sleep(delay)
            continue

        if not resp.ok:
            logging.error("Gemini REST error %s: %s", resp.status_code, resp.text[:2000])
            resp.raise_for_status()

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {json.dumps(data)[:1500]}")

        parts = (candidates[0].get("content") or {}).get("parts") or []
        if not parts or "text" not in parts[0]:
            raise RuntimeError(f"Gemini response missing text: {json.dumps(data)[:1500]}")

        return parts[0]["text"]

    raise last_exc
