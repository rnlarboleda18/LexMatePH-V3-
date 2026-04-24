"""Ensure statutes.id = 'RCC' exists (FK target for codal_case_links)."""
import json
import os
import sys
from pathlib import Path

import psycopg2

root = Path(__file__).resolve().parent.parent
vals = json.loads((root / "api" / "local.settings.json").read_text(encoding="utf-8")).get(
    "Values"
) or {}
db = (os.environ.get("DB_CONNECTION_STRING") or vals.get("DB_CONNECTION_STRING") or "").strip()
if not db:
    sys.exit("No DB_CONNECTION_STRING")

conn = psycopg2.connect(db)
cur = conn.cursor()
cur.execute(
    """
    INSERT INTO statutes (id, full_name, alias, category)
    SELECT %s, %s, %s, %s
    WHERE NOT EXISTS (SELECT 1 FROM statutes WHERE id = %s)
    """,
    (
        "RCC",
        "Revised Corporation Code of the Philippines",
        "RCC",
        "Corporate Law",
        "RCC",
    ),
)
conn.commit()
print("RCC statute rows inserted:", cur.rowcount)
cur.close()
conn.close()
