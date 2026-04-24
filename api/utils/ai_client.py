import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

import requests
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

# Lexify grading and other callers: override with GEMINI_VERTEX_MODEL. Use Flash on global Vertex for lower latency.
DEFAULT_MODEL = os.environ.get("GEMINI_VERTEX_MODEL") or "gemini-3-flash-preview"

logger = logging.getLogger(__name__)

_CLOUD_PLATFORM_SCOPE = ("https://www.googleapis.com/auth/cloud-platform",)

# Reuse OAuth credentials across concurrent Lexify calls (avoid a token refresh per question).
_vertex_creds_lock = threading.Lock()
_vertex_creds: Optional[Any] = None

# Keep-alive to Vertex (same process serves many parallel grades).
_http_session: Optional[requests.Session] = None
_http_session_lock = threading.Lock()


def _maybe_use_gcloud_application_default_credentials_file() -> None:
    """Help local `func start`: pick up `gcloud auth application-default login` without editing local.settings."""
    if (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip():
        return
    if os.name == "nt":
        appdata = (os.environ.get("APPDATA") or "").strip()
        if not appdata:
            return
        path = os.path.join(appdata, "gcloud", "application_default_credentials.json")
    else:
        path = os.path.join(os.path.expanduser("~"), ".config", "gcloud", "application_default_credentials.json")
    if path and os.path.isfile(path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path


def _get_google_credentials():
    """
    Credentials for Vertex (OAuth access token).

    Prefer inline JSON for Azure/serverless (GOOGLE_SERVICE_ACCOUNT_JSON).
    Otherwise use Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS
    file path, gcloud user creds, etc.).
    """
    raw = (
        os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        or os.environ.get("GOOGLE_CREDENTIALS_JSON")
        or ""
    ).strip()
    if raw:
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                "GOOGLE_SERVICE_ACCOUNT_JSON must be valid JSON (a Google service account key)."
            ) from e
        return service_account.Credentials.from_service_account_info(
            info, scopes=_CLOUD_PLATFORM_SCOPE
        )
    _maybe_use_gcloud_application_default_credentials_file()
    credentials, _ = google_auth_default(scopes=_CLOUD_PLATFORM_SCOPE)
    return credentials


def _vertex_generate_url(*, project_id: str, location: str, model: str) -> str:
    loc = (location or "global").strip()
    model = model.strip()
    if loc == "global":
        return (
            f"https://aiplatform.googleapis.com/v1/projects/{project_id}"
            f"/locations/global/publishers/google/models/{model}:generateContent"
        )
    return (
        f"https://{loc}-aiplatform.googleapis.com/v1/projects/{project_id}"
        f"/locations/{loc}/publishers/google/models/{model}:generateContent"
    )


def _get_vertex_bearer_token() -> str:
    global _vertex_creds
    with _vertex_creds_lock:
        if _vertex_creds is None:
            _vertex_creds = _get_google_credentials()
        if not _vertex_creds.valid:
            _vertex_creds.refresh(GoogleAuthRequest())
        token = _vertex_creds.token
        if not token:
            raise ValueError(
                "Could not get an OAuth access token for Vertex. "
                "Use a service account (e.g. GOOGLE_APPLICATION_CREDENTIALS) or valid ADC."
            )
        return token


def _vertex_http_session() -> requests.Session:
    global _http_session
    with _http_session_lock:
        if _http_session is None:
            s = requests.Session()
            s.headers.update({"Connection": "keep-alive"})
            _http_session = s
        return _http_session


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
    """
    Vertex AI generateContent only (no Gemini Developer API fallback).
    Requires GOOGLE_CLOUD_PROJECT and either GOOGLE_SERVICE_ACCOUNT_JSON (Azure)
    or ADC (e.g. GOOGLE_APPLICATION_CREDENTIALS to a key file locally).
    """
    project_id = (
        os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("VERTEX_AI_PROJECT") or ""
    ).strip()
    if not project_id:
        raise ValueError(
            "Vertex AI requires GOOGLE_CLOUD_PROJECT (or VERTEX_AI_PROJECT). "
            "There is no API-key fallback."
        )

    location = (
        os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("VERTEX_AI_LOCATION") or "global"
    ).strip()

    url = _vertex_generate_url(project_id=project_id, location=location, model=model)
    token = _get_vertex_bearer_token()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

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

    session = _vertex_http_session()
    last_error: Optional[str] = None
    for attempt in range(retries):
        try:
            response = session.post(url, headers=headers, data=json.dumps(payload), timeout=60)

            if response.status_code == 200:
                data = response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    logger.error("Vertex AI response structure error: %s", data)
                    raise ValueError(f"Invalid response structure from Vertex AI: {data}")

            if response.status_code in (429, 500, 502, 503, 504):
                last_error = f"HTTP {response.status_code}: {response.text}"
                wait_time = backoff_factor**attempt
                logger.warning(
                    "Vertex AI retry %s/%s after %ss: %s",
                    attempt + 1,
                    retries,
                    wait_time,
                    last_error,
                )
                time.sleep(wait_time)
                continue

            logger.error("Vertex AI error: HTTP %s: %s", response.status_code, response.text)
            raise ValueError(
                f"Vertex AI API returned error {response.status_code}: {response.text}"
            )

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            wait_time = backoff_factor**attempt
            logger.warning(
                "Vertex AI connection error (attempt %s/%s): %s",
                attempt + 1,
                retries,
                last_error,
            )
            time.sleep(wait_time)
            continue

    raise ValueError(f"Failed to call Vertex AI after {retries} attempts. Last error: {last_error}")


def call_vertex_ai_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Convenience wrapper for JSON mode (Vertex only)."""
    response_text = call_vertex_ai(
        prompt=prompt,
        system_instruction=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
        response_mime_type="application/json",
        model=model,
    )

    try:
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:-3].strip()
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:-3].strip()

        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from Vertex AI: %s", response_text)
        raise ValueError(f"Vertex AI returned invalid JSON: {e}") from e
