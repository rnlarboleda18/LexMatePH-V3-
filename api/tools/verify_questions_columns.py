"""One-off diagnostic: list public questions columns (no secrets). Run from api/: python tools/verify_questions_columns.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2  # noqa: E402

with open("local.settings.json", encoding="utf-8") as f:
    cs = json.load(f)["Values"].get("DB_CONNECTION_STRING", "").strip()
if not cs:
    sys.exit("Missing DB_CONNECTION_STRING")
conn = psycopg2.connect(cs)
cur = conn.cursor()
cur.execute(
    """
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'questions'
    ORDER BY ordinal_position
    """
)
cols = [r[0] for r in cur.fetchall()]
cur.close()
conn.close()
print("sub_topic present:", "sub_topic" in cols)
print("columns:", ", ".join(cols))
