"""Azure Cognitive Services Speech — SSML via REST only (no Speech SDK wheel; saves ~tens of MiB on Linux deploy)."""
import logging
import os
from typing import Optional

import requests

DEFAULT_REGION = "japaneast"
# RIFF WAV for browser/HttpResponse compatibility (matches prior SDK path).
OUTPUT_WAV = "riff-16khz-16bit-mono-pcm"


def synthesize_ssml_wav(
    ssml: str,
    *,
    subscription_key: str,
    region: str = DEFAULT_REGION,
    timeout: int = 120,
) -> bytes:
    if not subscription_key or "<insert" in subscription_key.lower():
        raise ValueError("Invalid or missing SPEECH_KEY")

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": OUTPUT_WAV,
    }
    resp = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=timeout)
    if resp.status_code != 200:
        logging.error("Azure Speech REST %s: %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
    return resp.content


def synthesize_plain_text_wav(
    text: str,
    *,
    voice_name: str,
    subscription_key: str,
    region: Optional[str] = None,
    rate: str = "0.85",
) -> bytes:
    """Build minimal SSML (escape XML) and return WAV bytes."""
    region = region or os.environ.get("SPEECH_REGION") or DEFAULT_REGION
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    ssml = (
        f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
        f"<voice name='{voice_name}'>"
        f"<prosody rate='{rate}'>{safe}</prosody>"
        f"</voice></speak>"
    )
    return synthesize_ssml_wav(ssml, subscription_key=subscription_key, region=region)
