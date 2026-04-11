"""
Apply RCC codal DDL + legal_codes row (see apply_rcc_codal_schema.sql).

Uses DB_CONNECTION_STRING from the environment or local.settings.json Values.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2


def _load_conn_str() -> str:
    s = (os.environ.get("DB_CONNECTION_STRING") or "").strip()
    if s:
        return s
    try:
        root = Path(__file__).resolve().parents[1]
        with open(root / "local.settings.json", encoding="utf-8") as f:
            vals = json.load(f).get("Values", {})
        return (vals.get("DB_CONNECTION_STRING") or "").strip()
    except OSError:
        return ""


def main() -> None:
    conn_str = _load_conn_str()
    if not conn_str:
        raise SystemExit("DB_CONNECTION_STRING not set and local.settings.json missing.")

    sql_path = Path(__file__).resolve().parent / "apply_rcc_codal_schema.sql"
    sql = sql_path.read_text(encoding="utf-8")

    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.close()
    print("RCC schema applied:", sql_path)


if __name__ == "__main__":
    main()
