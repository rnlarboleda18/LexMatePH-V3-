"""
Run manual VACUUM ANALYZE against cloud PostgreSQL.

Reads DB_CONNECTION_STRING from (in order): environment variable,
then api/local.settings.json Values.

Usage (from api/):
  python tools/run_cloud_vacuum.py              # whole database
  python tools/run_cloud_vacuum.py sc_decided_cases flashcard_concepts

Uses online VACUUM (not VACUUM FULL) — safe for production; can take several minutes.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import psycopg2

_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def _conn_string() -> str:
    env = (os.getenv("DB_CONNECTION_STRING") or os.getenv("DATABASE_URL") or "").strip()
    if env:
        return env
    root = Path(__file__).resolve().parents[1]
    cfg = root / "local.settings.json"
    if not cfg.is_file():
        print("Set DB_CONNECTION_STRING or create api/local.settings.json", file=sys.stderr)
        sys.exit(1)
    val = json.loads(cfg.read_text(encoding="utf-8")).get("Values", {}).get("DB_CONNECTION_STRING")
    if not val or not str(val).strip():
        print("DB_CONNECTION_STRING missing in local.settings.json", file=sys.stderr)
        sys.exit(1)
    return str(val).strip()


def main() -> None:
    tables = sys.argv[1:]
    for t in tables:
        if not _IDENT.match(t):
            print(f"Invalid table name: {t!r}", file=sys.stderr)
            sys.exit(1)

    cs = _conn_string()
    conn = psycopg2.connect(cs, connect_timeout=60)
    conn.autocommit = True
    cur = conn.cursor()
    if tables:
        q = ", ".join(tables)
        print(f"VACUUM ANALYZE {q} …")
        cur.execute(f"VACUUM ANALYZE {q}")
    else:
        print("VACUUM ANALYZE (whole database) …")
        cur.execute("VACUUM ANALYZE")
    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
