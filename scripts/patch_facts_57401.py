import json
import re
import psycopg2
import os

FAILED_FILE = "failed_digest_57401.txt"
CASE_ID = "57401"

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except Exception as e:
    print(f"Error loading settings: {e}")
    exit(1)

def patch_facts():
    print(f"Reading {FAILED_FILE}...")
    with open(FAILED_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract digest_facts using regex because the JSON is truncated/invalid
    # Looking for: "digest_facts": "..."
    # We need to be careful about escaped quotes inside the string.
    # Pattern: "digest_facts":\s*"(.*?)(?<!\\)"
    # But newlines might be literal \n in the file if it was dumped as a string representation, 
    # or actual newlines if it was dumped as formatted JSON. 
    # The file view shows it's formatted JSON (multiple lines).
    
    # Let's try to extract the value by finding the key and then parsing the string until the next unescaped quote.
    start_marker = '"digest_facts":'
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("Could not find digest_facts key.")
        return

    # Move past the marker and opening quote
    value_start = content.find('"', start_idx + len(start_marker)) + 1
    
    # Find end quote (ignoring escaped ones)
    current_idx = value_start
    while current_idx < len(content):
        if content[current_idx] == '"' and content[current_idx-1] != '\\':
            break
        current_idx += 1
    
    raw_value = content[value_start:current_idx]
    
    # Decode escape sequences (e.g. \n -> newline)
    # Using json.loads to decode the string specifically
    try:
        facts_decoded = json.loads(f'"{raw_value}"')
    except Exception as e:
        print(f"Error decoding extracted string: {e}")
        # Fallback: simple replace
        facts_decoded = raw_value.replace('\\n', '\n').replace('\\"', '"')

    # Double check formatting
    print("-" * 20)
    print("EXTRACTED RIGHTS:")
    print(facts_decoded[:200] + "...")
    print("-" * 20)
    
    if "The Antecedents" not in facts_decoded:
        print("WARNING: Extracted facts do not contain expected headers. Aborting patch.")
        return

    # Ensure double newlines for markdown
    facts_final = facts_decoded.replace('\n', '\n\n')
    # Clean up triple newlines if any
    while '\n\n\n' in facts_final:
        facts_final = facts_final.replace('\n\n\n', '\n\n')

    print("Patching database...")
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE sc_decided_cases SET digest_facts = %s WHERE id = %s",
            (facts_final, CASE_ID)
        )
        conn.commit()
        print(f"Successfully updated facts for Case {CASE_ID}")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    patch_facts()
