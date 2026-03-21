import psycopg2
import json
import sys
import os

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')
from blueprints.audio_provider import _get_text_for_codal

settings_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\local.settings.json'
with open(settings_path) as f:
    settings = json.load(f)

os.environ['DB_CONNECTION_STRING'] = settings['Values']['DB_CONNECTION_STRING']

with open('proof.txt', 'w', encoding='utf-8') as out:
    out.write("AUDIO LOOKUP COLLISION PROOF\n")
    out.write("==============================\n\n")

    def test(cid):
        text, title = _get_text_for_codal(cid, 'const')
        out.write(f"--- QUERYING CONTENT_ID: '{cid}' ---\n")
        out.write(f"Resulting Audio Text (Start): {text[:140]}...\n\n")

    out.write("1. LOOSE / SEQUENTIAL IDS (Simulating Old Playlist items):\n")
    test('1') # Will hit II-1 
    test('2') # Will hit II-2

    out.write("\n2. ABSOLUTE FIXED IDS (Simulating New Playlist items):\n")
    test('I-0')   # Article I
    test('III-1') # Article III Sec 1

print("Proof output written to proof.txt")
