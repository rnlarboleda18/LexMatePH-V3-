"""Add decided_under column to codal_case_links for BP 68 → RCC tagging."""
import json, psycopg2
from pathlib import Path

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor()

# Check if column already exists
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema='public'
      AND table_name='codal_case_links'
      AND column_name='decided_under'
""")
if cur.fetchone():
    print("Column 'decided_under' already exists — nothing to do.")
else:
    cur.execute("""
        ALTER TABLE codal_case_links
        ADD COLUMN decided_under VARCHAR(20) DEFAULT NULL
    """)
    conn.commit()
    print("Added column: codal_case_links.decided_under VARCHAR(20)")

cur.close()
conn.close()
