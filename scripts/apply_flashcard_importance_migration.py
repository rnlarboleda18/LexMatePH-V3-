#!/usr/bin/env python3
"""Apply sql/flashcard_concepts_importance_migration.sql (CLI). Uses DB_CONNECTION_STRING or api/local.settings.json."""
from __future__ import annotations

import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SQL = os.path.join(_ROOT, "sql", "flashcard_concepts_importance_migration.sql")
_API = os.path.join(_ROOT, "api")
if _API not in sys.path:
    sys.path.insert(0, _API)


def _conn_str() -> str:
    env = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if env:
        return env.replace(":6432/", ":5432/")
    path = os.path.join(_API, "local.settings.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            v = (json.load(f).get("Values") or {}).get("DB_CONNECTION_STRING", "").strip()
        if v:
            return v.replace(":6432/", ":5432/")
    print("Set DB_CONNECTION_STRING or Values.DB_CONNECTION_STRING in api/local.settings.json")
    sys.exit(1)
    return ""


def _statements(sql_text: str) -> list[str]:
    lines = []
    for line in sql_text.splitlines():
        cut = line.find("--")
        if cut >= 0:
            line = line[:cut]
        lines.append(line)
    text = "\n".join(lines)
    parts = []
    for chunk in re.split(r";\s*\n", text):
        c = chunk.strip()
        if c:
            parts.append(c if c.endswith(";") else c + ";")
    return parts


def main() -> None:
    if not os.path.isfile(_SQL):
        print(f"Missing {_SQL}")
        sys.exit(1)
    with open(_SQL, encoding="utf-8") as f:
        sql_text = f.read()
    stmts = _statements(sql_text)
    import psycopg2

    conn = psycopg2.connect(_conn_str(), connect_timeout=120)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        for i, s in enumerate(stmts, 1):
            cur.execute(s)
            print(f"[{i}/{len(stmts)}] ok")
    finally:
        cur.close()
        conn.close()
    print("Migration applied.")


if __name__ == "__main__":
    main()
