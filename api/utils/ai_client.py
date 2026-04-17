import os
import json
import requests
import time
import logging
from typing import List, Dict, Any, Optional, Union

# Configuration
DEFAULT_MODEL = os.environ.get("GEMINI_VERTEX_MODEL") or "gemini-2.5-flash-lite"
API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

logger = logging.getLogger(__name__)

def call_vertex_ai(
    prompt: Union[str, List[Dict[str, Any]]],
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    response_mime_type: str = "text/plain",
    model: str = DEFAULT_MODEL,
    retries: int = 3,
    backoff_factor: float = 1.5
) -> str:
    """
    Unified call to Google Vertex AI REST API (generateContent).
    """
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set.")

    url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent?key={API_KEY}"
    
    # Standardize contents structure
    if isinstance(prompt, str):
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
    else:
        contents = prompt

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": response_mime_type
        }
    }

    if system_instruction:
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction}]
        }

    headers = {"Content-Type": "application/json"}
    
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                try:
                    return data['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    logger.error(f"Vertex AI response structure error: {data}")
                    raise ValueError(f"Invalid response structure from Vertex AI: {data}")
            
            # Handle retryable errors (5xx and 429)
            if response.status_code in [429, 500, 502, 503, 504]:
                last_error = f"HTTP {response.status_code}: {response.text}"
                wait_time = backoff_factor ** attempt
                logger.warning(f"Vertex AI retry {attempt+1}/{retries} after {wait_time}s due to error: {last_error}")
                time.sleep(wait_time)
                continue
            else:
                # Terminal error
                logger.error(f"Vertex AI Error: HTTP {response.status_code}: {response.text}")
                raise ValueError(f"Vertex AI API returned error {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            wait_time = backoff_factor ** attempt
            logger.warning(f"Vertex AI Connection error (attempt {attempt+1}/{retries}): {last_error}")
            time.sleep(wait_time)
            continue

    raise ValueError(f"Failed to call Vertex AI after {retries} attempts. Last error: {last_error}")

def call_vertex_ai_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    model: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Convenience wrapper for JSON mode.
    """
    response_text = call_vertex_ai(
        prompt=prompt,
        system_instruction=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
        response_mime_type="application/json",
        model=model
    )
    
    try:
        # Vertex AI JSON mode sometimes wraps in triple backticks even if asked for application/json
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:-3].strip()
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:-3].strip()
            
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Vertex AI: {response_text}")
        raise ValueError(f"Vertex AI returned invalid JSON: {e}")
