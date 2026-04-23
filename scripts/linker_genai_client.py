"""
Shared Google GenAI client for codal linker scripts — Vertex AI only (ADC).

Authentication: Application Default Credentials only (``gcloud auth application-default login``
or ``GOOGLE_APPLICATION_CREDENTIALS``). API keys are not used for linkers.

Required:
  GOOGLE_CLOUD_PROJECT — GCP project id

Optional:
  GOOGLE_CLOUD_LOCATION — region (default ``global``, per Gemini 3 Flash global endpoint)
  GEMINI_LINKER_MODEL — override model id (default: :data:`DEFAULT_LINKER_VERTEX_MODEL`)

Missing keys are filled from ``api/local.settings.json`` (``Values``) when that file exists,
only for environment variables that are unset or empty.

Probe availability::

    python scripts/linker_genai_client.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Vertex model id (public preview) — see Google Cloud "Gemini 3 Flash" model docs.
DEFAULT_LINKER_VERTEX_MODEL = "gemini-3-flash-preview"

_genai_client = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def merge_local_settings_into_env() -> None:
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


def get_linker_genai_client():
    """Return a shared ``google.genai.Client`` using Vertex AI and ADC."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    merge_local_settings_into_env()
    from google import genai

    project = (
        os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("VERTEX_AI_PROJECT") or ""
    ).strip()
    if not project:
        raise RuntimeError(
            "Linkers require Vertex AI: set GOOGLE_CLOUD_PROJECT and use ADC "
            "(gcloud auth application-default login or GOOGLE_APPLICATION_CREDENTIALS)."
        )

    location = (
        os.environ.get("GOOGLE_CLOUD_LOCATION")
        or os.environ.get("VERTEX_AI_LOCATION")
        or "global"
    ).strip()

    _genai_client = genai.Client(vertexai=True, project=project, location=location)
    return _genai_client


def get_linker_model_name(*, fallback: str | None = None) -> str:
    """Resolved model id: ``GEMINI_LINKER_MODEL`` env, else ``fallback``, else default Flash 3 preview."""
    merge_local_settings_into_env()
    m = (os.environ.get("GEMINI_LINKER_MODEL") or "").strip()
    if m:
        return m
    if fallback:
        return fallback
    return DEFAULT_LINKER_VERTEX_MODEL


def probe_linker_vertex() -> None:
    """One minimal ``generateContent`` call to verify ADC, project, location, and model."""
    merge_local_settings_into_env()
    from google import genai

    client = get_linker_genai_client()
    model = get_linker_model_name()
    project = (
        os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("VERTEX_AI_PROJECT") or ""
    ).strip()
    location = (
        os.environ.get("GOOGLE_CLOUD_LOCATION")
        or os.environ.get("VERTEX_AI_LOCATION")
        or "global"
    ).strip()

    print(f"Vertex probe: project={project!r} location={location!r} model={model!r}")
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
        probe_linker_vertex()
    except Exception as exc:
        print("PROBE_FAILED:", exc, file=sys.stderr)
        sys.exit(1)
