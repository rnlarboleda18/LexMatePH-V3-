import psycopg2
import sys
import os
import json

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')
from blueprints.audio_provider import _get_text_for_codal

settings_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\local.settings.json'
with open(settings_path) as f:
    settings = json.load(f)

os.environ['DB_CONNECTION_STRING'] = settings['Values']['DB_CONNECTION_STRING']

def test_id(cid):
    text, title = _get_text_for_codal(cid, 'const')
    print(f"\n--- ID: {cid} ---")
    print(f"Title: {title}")
    print(f"Text Snippet: {text[:200]}...")

test_id('I-0')      # Article I
test_id('II-0')     # Article II Header
test_id('II-1')     # Article II Sec 1
test_id('III-1')    # Article III Sec 1
test_id('IV-1')     # Article IV Sec 1
