"""
ai_client.py — Google GenAI client (Vertex AI).

Auth: Vertex AI service account (GOOGLE_APPLICATION_CREDENTIALS or GCP_SA_JSON_B64).
      Falls back to Application Default Credentials (ADC) in production on GCP.

Project/location pulled from config.py (GCP_PROJECT, GCP_LOCATION).

Model: GEMINI_VERTEX_MODEL env var, default gemini-2.5-flash.
Fallback model: GEMINI_DIGEST_FALLBACK_MODEL, default gemini-2.5-flash.
"""
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

DEFAULT_MODEL  = os.environ.get("GEMINI_VERTEX_MODEL") or os.environ.get("GEMINI_DIGEST_MODEL") or "gemini-2.5-flash"
FALLBACK_MODEL = os.environ.get("GEMINI_DIGEST_FALLBACK_MODEL") or "gemini-2.5-flash"

_client = None
_client_lock = threading.Lock()


def _get_client():
    """Return a lazily-initialised Vertex AI GenAI client (shared, thread-safe)."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        import config
        from google import genai
        from google.genai import types as genai_types
        _client = genai.Client(
            vertexai=True,
            project=config.GCP_PROJECT,
            location=config.GCP_LOCATION,
            http_options=genai_types.HttpOptions(timeout=120_000),
        )
        logger.info(
            "Vertex AI GenAI client initialised — project=%s location=%s",
            config.GCP_PROJECT, config.GCP_LOCATION,
        )
    return _client


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
    """Generate content via Vertex AI using the google-genai SDK."""
    from google import genai
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

    if isinstance(prompt, str):
        contents = prompt
    else:
        contents = prompt

    cfg = genai.types.GenerateContentConfig(
        response_mime_type=response_mime_type,
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction or None,
    )

    client = _get_client()
    last_error: Optional[str] = None

    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=cfg,
            )
            return resp.text or ""
        except (ResourceExhausted, ServiceUnavailable) as e:
            last_error = str(e)
            wait = backoff_factor ** attempt
            logger.warning("Vertex AI retry %s/%s in %.1fs: %s", attempt + 1, retries, wait, e)
            time.sleep(wait)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e):
                last_error = str(e)
                wait = backoff_factor ** attempt
                logger.warning("Vertex AI retry %s/%s in %.1fs: %s", attempt + 1, retries, wait, e)
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Vertex AI failed after {retries} attempts. Last error: {last_error}")


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
        logger.error("Vertex AI returned invalid JSON: %s", text)
        raise ValueError(f"Vertex AI returned invalid JSON: {e}") from e
