"""
ai_client.py — Google GenAI client (Vertex AI or AI Studio API key).

Auth priority:
  1. GEMINI_API_KEY set → Google AI Studio (api_key mode, no GCP project needed)
  2. No API key        → Vertex AI via Application Default Credentials (ADC)

Local dev with AI Studio: set GEMINI_API_KEY in api/local.settings.json.
Production (Vertex AI):   set GCP_SA_JSON_B64 or GCP_SA_JSON in Azure App Settings,
                          OR rely on the managed identity / ADC on the host.

Default model : gemini-2.5-pro   (override: GEMINI_DEFAULT_MODEL)
Fallback model: gemini-2.5-flash  (override: GEMINI_FALLBACK_MODEL)
"""
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

DEFAULT_MODEL  = os.environ.get("GEMINI_DEFAULT_MODEL",  "").strip() or "gemini-2.5-pro"
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "").strip() or "gemini-2.5-flash"
# Non-thinking fast model for time-sensitive batch calls (e.g. lexify_grade_batch).
# Must complete 20-item grading within the SWA Free tier 60s timeout.
BATCH_MODEL    = os.environ.get("GEMINI_BATCH_MODEL",    "").strip() or "gemini-2.5-flash"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

_client = None
_client_lock = threading.Lock()


def _get_client():
    """Return a lazily-initialised GenAI client (shared, thread-safe).

    Uses Vertex AI exclusively.
    """
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        from google import genai
        from google.genai import types as genai_types
        import config

        # Force Vertex AI exclusively
        _client = genai.Client(
            vertexai=True,
            project=config.GCP_PROJECT,
            location=config.GCP_LOCATION,
            http_options=genai_types.HttpOptions(timeout=120_000),
        )
        logger.info(
            "Vertex AI client initialised exclusively — project=%s location=%s default=%s fallback=%s",
            config.GCP_PROJECT, config.GCP_LOCATION, DEFAULT_MODEL, FALLBACK_MODEL,
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
    thinking_budget: Optional[int] = None,
) -> str:
    """Generate content via Vertex AI or AI Studio."""
    from google import genai
    from google.genai import types as genai_types

    cfg_kwargs = dict(
        response_mime_type=response_mime_type,
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction or None,
    )
    if thinking_budget is not None:
        cfg_kwargs["thinking_config"] = genai_types.ThinkingConfig(thinking_budget=thinking_budget)
    cfg = genai.types.GenerateContentConfig(**cfg_kwargs)

    client = _get_client()
    last_error: Optional[str] = None

    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=cfg,
            )
            return resp.text or ""
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "503" in err or "502" in err:
                last_error = err
                wait = backoff_factor ** attempt
                logger.warning("Vertex AI retry %s/%s (model=%s) in %.1fs: %s", attempt + 1, retries, model, wait, e)
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Vertex AI failed after {retries} attempts (model={model}). Last error: {last_error}")


def call_vertex_ai_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    model: str = DEFAULT_MODEL,
    thinking_budget: Optional[int] = None,
) -> Dict[str, Any]:
    """JSON-mode call — tries the given model, falls back to FALLBACK_MODEL."""
    def _try(m: str) -> str:
        return call_vertex_ai(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type="application/json",
            model=m,
            thinking_budget=thinking_budget,
        )

    fallback = FALLBACK_MODEL if model != FALLBACK_MODEL else DEFAULT_MODEL
    try:
        text = _try(model)
    except Exception as primary_err:
        logger.warning("Primary model %s failed (%s); trying fallback %s", model, primary_err, fallback)
        text = _try(fallback)

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


_studio_client = None
_studio_client_lock = threading.Lock()


def _get_ai_studio_client():
    """Return a lazily-initialised AI Studio GenAI client specifically for Lexify."""
    global _studio_client
    if _studio_client is not None:
        return _studio_client
    with _studio_client_lock:
        if _studio_client is not None:
            return _studio_client
        # Vertex AI exclusive redirect
        logger.warning("Lexify requested AI Studio client, but Vertex AI is forced. Returning Vertex AI client instead.")
        _studio_client = _get_client()
    return _studio_client


def call_lexify_ai(
    prompt: Union[str, List[Dict[str, Any]]],
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    response_mime_type: str = "text/plain",
    model: str = DEFAULT_MODEL,
    retries: int = 3,
    backoff_factor: float = 1.5,
    thinking_budget: Optional[int] = None,
) -> str:
    """Generate content exclusively via Google AI Studio for Lexify."""
    from google import genai
    from google.genai import types as genai_types

    cfg_kwargs = dict(
        response_mime_type=response_mime_type,
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction or None,
    )
    if thinking_budget is not None:
        cfg_kwargs["thinking_config"] = genai_types.ThinkingConfig(thinking_budget=thinking_budget)
    cfg = genai.types.GenerateContentConfig(**cfg_kwargs)

    client = _get_ai_studio_client()
    last_error: Optional[str] = None

    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=cfg,
            )
            return resp.text or ""
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "503" in err or "502" in err:
                last_error = err
                wait = backoff_factor ** attempt
                logger.warning("Lexify AI Studio retry %s/%s (model=%s) in %.1fs: %s", attempt + 1, retries, model, wait, e)
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Lexify AI Studio failed after {retries} attempts (model={model}). Last error: {last_error}")


def call_lexify_ai_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    model: str = DEFAULT_MODEL,
    thinking_budget: Optional[int] = None,
) -> Dict[str, Any]:
    """JSON-mode call for Lexify — tries the given model via AI Studio, falls back to FALLBACK_MODEL."""
    def _try(m: str) -> str:
        return call_lexify_ai(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type="application/json",
            model=m,
            thinking_budget=thinking_budget,
        )

    fallback = FALLBACK_MODEL if model != FALLBACK_MODEL else DEFAULT_MODEL
    try:
        text = _try(model)
    except Exception as primary_err:
        logger.warning("Lexify primary AI Studio model %s failed (%s); trying fallback %s", model, primary_err, fallback)
        text = _try(fallback)

    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:-3].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:-3].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Lexify AI Studio returned invalid JSON: %s", text)
        raise ValueError(f"Lexify AI Studio returned invalid JSON: {e}") from e

