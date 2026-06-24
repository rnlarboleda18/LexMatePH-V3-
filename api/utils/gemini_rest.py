"""Minimal Gemini calls mapped to Vertex AI (exclusively)."""
import json
import logging
from typing import Any, Dict, Optional

from utils.ai_client import call_vertex_ai

def gemini_generate_text(
    model: str,
    prompt: str,
    *,
    response_mime_type: Optional[str] = None,
    generation_config: Optional[Dict[str, Any]] = None,
    timeout: int = 300,
) -> str:
    """Redirect to Vertex AI call_vertex_ai exclusively."""
    # Map model to standard supported Vertex AI models
    if "gemini-3-flash" in model or "gemini-3.1" in model or "flash" in model:
        vertex_model = "gemini-3.5-flash"
    else:
        vertex_model = "gemini-2.5-flash"

    temperature = 0.2
    max_tokens = 4096
    if generation_config:
        temperature = generation_config.get("temperature", temperature)
        max_tokens = generation_config.get("maxOutputTokens") or generation_config.get("max_output_tokens") or max_tokens

    logging.info(
        "gemini_generate_text: redirecting '%s' to Vertex AI model '%s'",
        model, vertex_model
    )
    return call_vertex_ai(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_mime_type=response_mime_type or "text/plain",
        model=vertex_model,
    )

