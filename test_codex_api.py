import sys
import os
import json
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- FETCHING ARTICLE_VERSIONS FOR 7 AND 8 ---")
cur.execute("SELECT version_id, article_number FROM article_versions WHERE code_id = (SELECT code_id FROM legal_codes WHERE short_name = 'fc' OR short_name = 'FC' LIMIT 1) AND article_number IN ('7', '8')")
rows = cur.fetchall()
for r in rows:
    v_id = r[0]
    num = r[1]
    print(f"Row {num}: UUID {v_id}")

print("\n--- FETCHING CODEX.PY FOR FC ---")
sys.path.insert(0, os.path.abspath('api/blueprints'))
import codex
from db_pool import put_db_connection

# Mock the function by directly executing what codex.py executes for FC
cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'fc' OR short_name = 'FC'")
fc_code_id = cur.fetchone()[0]

cur.execute("""
    SELECT version_id, article_number, content 
    FROM article_versions 
    WHERE code_id = %s AND article_number IN ('7', '8')
""", (fc_code_id,))
for r in cur.fetchall():
    print(f"codex.py sees: Article {r[1]}, ID={r[0]}")
    print(repr(r[2][:50]))

conn.close()
