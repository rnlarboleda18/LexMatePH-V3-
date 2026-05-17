"""
Find correct LawPhil URLs for SC issuances using Gemini + Google Search,
then verify with HTTP HEAD.
"""
from __future__ import annotations
import sys
import requests
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "api"))

from linker_genai_client import get_linker_genai_client, merge_local_settings_into_env
from google import genai
from google.genai import types as genai_types

merge_local_settings_into_env()

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LexMatePH-Research/1.0)"}
MODEL   = "gemini-2.5-pro"

def check_url(url: str) -> bool:
    try:
        r = requests.head(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False

TARGETS = [
    {
        "statute_id": "AM-08-1-16-SC",
        "name": "Rule on the Writ of Habeas Data A.M. No. 08-1-16-SC 2008",
    },
    {
        "statute_id": "AM-02-8-13-SC",
        "name": "2004 Rules on Notarial Practice A.M. No. 02-8-13-SC",
    },
    {
        "statute_id": "NCJC",
        "name": "New Code of Judicial Conduct for the Philippine Judiciary A.M. No. 03-05-01-SC 2004",
    },
]

client = get_linker_genai_client()
google_search_tool = genai_types.Tool(google_search=genai_types.GoogleSearch())

for t in TARGETS:
    print(f"\n{'='*60}")
    print(f"[{t['statute_id']}] {t['name']}")
    prompt = (
        f"I need to find the exact working URL on lawphil.net for this Philippine Supreme Court issuance:\n"
        f"  {t['name']}\n\n"
        f"KNOWN WORKING PATTERN: The Writ of Amparo (A.M. No. 07-9-12-SC, 2007) is at:\n"
        f"  https://lawphil.net/judjuris/juri2007/sep2007/am_07-9-12-sc_2007.html\n\n"
        f"The pattern is: lawphil.net/judjuris/juri{{YEAR}}/{{3-letter-month}}{{YEAR}}/am_{{##-#-##}}-sc_{{year}}.html\n\n"
        f"Use Google Search to find the exact promulgation date (month and year) of this issuance, "
        f"then construct the URL following the same pattern. "
        f"Search for: lawphil.net {t['name']} URL\n\n"
        f"Return ONLY the URL, nothing else. If you cannot confirm it exists, try the most likely month. "
        f"Format: https://lawphil.net/judjuris/..."
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            tools=[google_search_tool],
            temperature=0,
        ),
    )
    url = (resp.text or "").strip()
    # Strip any trailing punctuation or extra text
    url = url.split()[0] if url else ""
    alive = check_url(url) if url.startswith("http") else False
    status = "200 OK" if alive else "FAIL"
    print(f"  URL [{status}]: {url}")
