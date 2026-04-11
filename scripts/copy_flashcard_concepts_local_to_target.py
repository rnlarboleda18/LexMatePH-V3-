#!/usr/bin/env python3
"""
Copy merged legal concepts into flashcard_concepts using a LOCAL source DB and a TARGET DB.

Reads sc_decided_cases.legal_concepts from SOURCE with the same filters as the app:
  - decision year BETWEEN 1987 AND 2025 (see api/utils/flashcard_legal_concepts.py)
  - division ILIKE '%en banc%'

Writes to TARGET: TRUNCATE flashcard_concepts + batched INSERT.

Use when cloud flashcard_concepts is empty but your local DB has digest data (fast local read).

Environment (first non-empty wins per role):
  Source: SOURCE_DB_CONNECTION_STRING, LOCAL_DB_CONNECTION_STRING,
          or Values.LOCAL_DB_CONNECTION_STRING in api/local.settings.json
  Target: TARGET_DB_CONNECTION_STRING, DB_CONNECTION_STRING,
          or Values.DB_CONNECTION_STRING in api/local.settings.json

Usage:
  set LOCAL_DB_CONNECTION_STRING=postgresql://user:pass@localhost:5432/dbname
  set DB_CONNECTION_STRING=postgresql://...cloud...
  python scripts/copy_flashcard_concepts_local_to_target.py --dry-run

  python scripts/copy_flashcard_concepts_local_to_target.py
  python scripts/copy_flashcard_concepts_local_to_target.py --source "..." --target "..."
"""

from __future__ import annotations

import argparse
from typing import Optional
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_API = os.path.join(_ROOT, "api")
if _API not in sys.path:
    sys.path.insert(0, _API)


def _normalize_port(conn: str) -> str:
    if ":5432/" in conn:
        return conn.replace(":5432/", ":5432/")
    return conn


def _from_settings(key: str) -> str:
    settings_path = os.path.join(_API, "local.settings.json")
    if not os.path.isfile(settings_path):
        return ""
    with open(settings_path, encoding="utf-8") as f:
        data = json.load(f)
    return (data.get("Values") or {}).get(key, "").strip()


def resolve_source_url(explicit: Optional[str]) -> str:
    if explicit and explicit.strip():
        return _normalize_port(explicit.strip())
    for k in ("SOURCE_DB_CONNECTION_STRING", "LOCAL_DB_CONNECTION_STRING"):
        v = os.environ.get(k, "").strip()
        if v:
            return _normalize_port(v)
    v = _from_settings("LOCAL_DB_CONNECTION_STRING")
    if v:
        return _normalize_port(v)
    return ""


def resolve_target_url(explicit: Optional[str]) -> str:
    if explicit and explicit.strip():
        return _normalize_port(explicit.strip())
    for k in ("TARGET_DB_CONNECTION_STRING", "DB_CONNECTION_STRING"):
        v = os.environ.get(k, "").strip()
        if v:
            return _normalize_port(v)
    v = _from_settings("DB_CONNECTION_STRING")
    if v:
        return _normalize_port(v)
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Local digest -> target flashcard_concepts table")
    parser.add_argument("--source", default=None, help="Postgres URL for local/source DB (else env/settings)")
    parser.add_argument("--target", default=None, help="Postgres URL for target DB (else env/settings)")
    parser.add_argument("--dry-run", action="store_true", help="Read local + merge only; do not write target")
    parser.add_argument("--batch-size", type=int, default=800, help="Insert batch size (default 800)")
    args = parser.parse_args()

    src = resolve_source_url(args.source)
    tgt = resolve_target_url(args.target)

    if not src:
        print(
            "Missing source connection. Set SOURCE_DB_CONNECTION_STRING or LOCAL_DB_CONNECTION_STRING, "
            "or add Values.LOCAL_DB_CONNECTION_STRING to api/local.settings.json, or pass --source."
        )
        sys.exit(1)
    if not args.dry_run and not tgt:
        print(
            "Missing target connection. Set TARGET_DB_CONNECTION_STRING or DB_CONNECTION_STRING, "
            "or Values.DB_CONNECTION_STRING in api/local.settings.json, or pass --target."
        )
        sys.exit(1)

    import psycopg2
    from psycopg2.extras import Json, RealDictCursor, execute_values

    from utils.flashcard_legal_concepts import (
        FLASHCARD_SOURCE_DIVISION_PATTERN,
        FLASHCARD_SOURCE_YEAR_MAX,
        FLASHCARD_SOURCE_YEAR_MIN,
        flashcard_digest_select_sql_and_params,
        merge_digest_rows_to_concepts_list,
        term_key_for_term,
    )

    t0 = time.perf_counter()
    print(
        f"Filter: year {FLASHCARD_SOURCE_YEAR_MIN}-{FLASHCARD_SOURCE_YEAR_MAX}, "
        f"division ILIKE {FLASHCARD_SOURCE_DIVISION_PATTERN!r}"
    )

    print("Connecting to SOURCE (local)...")
    sconn = psycopg2.connect(src, connect_timeout=120)
    try:
        scur = sconn.cursor(cursor_factory=RealDictCursor)
        sql_fb, params_fb = flashcard_digest_select_sql_and_params()
        scur.execute(sql_fb, params_fb)
        rows = scur.fetchall() or []
        scur.close()
    finally:
        sconn.close()

    t_read = time.perf_counter()
    print(f"[timing] source SELECT: {t_read - t0:.2f}s, digest rows={len(rows)}")

    merged = merge_digest_rows_to_concepts_list(rows)
    print(f"Deduplicated concepts: {len(merged)}")

    if args.dry_run:
        print("Dry run - target database not modified.")
        print(f"[timing] total: {time.perf_counter() - t0:.2f}s")
        return

    if not merged:
        print("Nothing to insert (0 concepts after merge). Exiting without truncating target.")
        sys.exit(0)

    print("Connecting to TARGET...")
    tconn = psycopg2.connect(tgt, connect_timeout=120)
    tconn.autocommit = False
    try:
        tcur = tconn.cursor()
        tcur.execute("TRUNCATE flashcard_concepts RESTART IDENTITY")

        tuples = [
            (
                term_key_for_term(c["term"]),
                c["term"],
                c.get("definition") or "",
                Json(c.get("sources") or []),
                int(c.get("case_count") or 0),
                "core",
            )
            for c in merged
        ]
        batch = args.batch_size
        ins0 = time.perf_counter()
        for i in range(0, len(tuples), batch):
            chunk = tuples[i : i + batch]
            execute_values(
                tcur,
                """
                INSERT INTO flashcard_concepts (term_key, term, definition, sources, case_count, importance_tier)
                VALUES %s
                """,
                chunk,
                template="(%s, %s, %s, %s::jsonb, %s, %s)",
                page_size=len(chunk),
            )
            if len(tuples) > batch:
                print(f"  inserted {min(i + batch, len(tuples))}/{len(tuples)} …")

        tconn.commit()
        print(f"[timing] target INSERT: {time.perf_counter() - ins0:.2f}s")
        print(f"Done. {len(merged)} rows in target flashcard_concepts.")
        print(f"[timing] total: {time.perf_counter() - t0:.2f}s")
    finally:
        tconn.close()


if __name__ == "__main__":
    main()
