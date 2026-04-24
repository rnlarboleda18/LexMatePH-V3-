import json
import os
from pathlib import Path

import psycopg2


def _db_url() -> str:
    direct = (os.environ.get("DB_CONNECTION_STRING") or "").strip()
    if direct:
        return direct
    path = Path(__file__).resolve().parent.parent / "api" / "local.settings.json"
    if path.is_file():
        try:
            vals = json.loads(path.read_text(encoding="utf-8")).get("Values") or {}
            v = str(vals.get("DB_CONNECTION_STRING") or "").strip()
            if v:
                return v
        except (OSError, json.JSONDecodeError):
            pass
    return "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"


conn = psycopg2.connect(_db_url())
cur = conn.cursor()

cur.execute("DELETE FROM codal_case_links WHERE statute_id = 'RPC'")
deleted = cur.rowcount
conn.commit()

print(f"✅ Deleted {deleted} RPC links from database")

conn.close()
