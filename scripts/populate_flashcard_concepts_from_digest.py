#!/usr/bin/env python3
"""
Create/populate flashcard_concepts from sc_decided_cases.legal_concepts (case digest data).

Source rows are filtered to: decision years 1987 through 2025 and division matching En Banc (see api/utils/flashcard_legal_concepts.py).

Prerequisites:
  1. Run sql/flashcard_concepts_importance_migration.sql (and your base flashcard_concepts DDL if needed).
  2. Set DB_CONNECTION_STRING (e.g. from api/local.settings.json Values).

After repopulating, re-run scripts/label_flashcard_importance.py if you use importance_tier (TRUNCATE clears labels).

Why it was slow before: one INSERT per concept (10k+ round trips to cloud Postgres).
This version uses batched INSERTs (execute_values) in chunks.

Usage:
  python scripts/populate_flashcard_concepts_from_digest.py
  python scripts/populate_flashcard_concepts_from_digest.py --dry-run

To fill cloud flashcard_concepts from a local Postgres (same filters), use:
  scripts/copy_flashcard_concepts_local_to_target.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_API = os.path.join(_ROOT, "api")
if _API not in sys.path:
    sys.path.insert(0, _API)


def _load_db_url() -> str:
    env = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if env:
        return env
    settings_path = os.path.join(_API, "local.settings.json")
    if os.path.isfile(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        return (data.get("Values") or {}).get("DB_CONNECTION_STRING", "").strip()
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Compute counts only; do not write.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=800,
        help="Rows per INSERT batch (default 800). Lower if memory-constrained.",
    )
    args = parser.parse_args()

    conn_str = _load_db_url()
    if not conn_str:
        print("DB_CONNECTION_STRING not set and api/local.settings.json missing Values.DB_CONNECTION_STRING.")
        sys.exit(1)

    if ":5432/" in conn_str:
        conn_str = conn_str.replace(":5432/", ":5432/")

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
    # connect_timeout avoids hanging forever; cloud DB can still be slow on first packet
    conn = psycopg2.connect(conn_str, connect_timeout=120)
    conn.autocommit = False
    t_connect = time.perf_counter()
    print(f"[timing] connect: {t_connect - t0:.2f}s")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        t_q0 = time.perf_counter()
        sql_fb, params_fb = flashcard_digest_select_sql_and_params()
        print(
            f"Filter: EXTRACT(YEAR FROM date) BETWEEN {FLASHCARD_SOURCE_YEAR_MIN} AND {FLASHCARD_SOURCE_YEAR_MAX}, "
            f"division ILIKE {FLASHCARD_SOURCE_DIVISION_PATTERN!r}"
        )
        cur.execute(sql_fb, params_fb)
        rows = cur.fetchall() or []
        t_fetch = time.perf_counter()
        print(f"[timing] SELECT digest rows: {t_fetch - t_q0:.2f}s (rows={len(rows)})")

        t_m0 = time.perf_counter()
        merged = merge_digest_rows_to_concepts_list(rows)
        t_merge = time.perf_counter()
        print(f"[timing] merge/dedupe in Python: {t_merge - t_m0:.2f}s")

        print(f"Digest cases with legal_concepts: {len(rows)}")
        print(f"Deduplicated flashcard concepts: {len(merged)}")

        if args.dry_run:
            conn.rollback()
            print("Dry run - no database changes.")
            print(
                f"[timing] total: {time.perf_counter() - t0:.2f}s — "
                "Slowness is usually (1) fetching many digest rows (large JSON over the wire), "
                "(2) cloud RTT on thousands of single INSERTs (use batched inserts), "
                "or (3) Python merge CPU on huge case counts."
            )
            return

        t_tr0 = time.perf_counter()
        cur.execute("TRUNCATE flashcard_concepts RESTART IDENTITY")
        t_tr = time.perf_counter()
        print(f"[timing] TRUNCATE: {t_tr - t_tr0:.2f}s")

        if not merged:
            conn.commit()
            print("No concepts to insert (merged list empty).")
            print(f"[timing] total: {time.perf_counter() - t0:.2f}s")
            try:
                from cache import cache_delete
                from config import FLASHCARD_CONCEPTS_CACHE_KEY

                cache_delete(FLASHCARD_CONCEPTS_CACHE_KEY)
            except Exception as inv_ex:
                print(f"[note] Redis flashcard cache invalidation skipped: {inv_ex}")
            return

        batch = args.batch_size
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

        t_ins0 = time.perf_counter()
        inserted = 0
        for i in range(0, len(tuples), batch):
            chunk = tuples[i : i + batch]
            execute_values(
                cur,
                """
                INSERT INTO flashcard_concepts (term_key, term, definition, sources, case_count, importance_tier)
                VALUES %s
                """,
                chunk,
                template="(%s, %s, %s, %s::jsonb, %s, %s)",
                page_size=len(chunk),
            )
            inserted += len(chunk)
            if len(tuples) > batch:
                print(f"  inserted {inserted}/{len(tuples)} …")

        conn.commit()
        t_ins = time.perf_counter()
        print(f"[timing] batched INSERTs ({len(tuples)} rows, batch_size={batch}): {t_ins - t_ins0:.2f}s")
        print(f"Inserted {len(merged)} rows into flashcard_concepts.")
        print(f"[timing] total: {time.perf_counter() - t0:.2f}s")

        try:
            from cache import cache_delete
            from config import FLASHCARD_CONCEPTS_CACHE_KEY

            if cache_delete(FLASHCARD_CONCEPTS_CACHE_KEY):
                print(f"Invalidated Redis key {FLASHCARD_CONCEPTS_CACHE_KEY!r} (next API request rebuilds cache).")
        except Exception as inv_ex:
            print(f"[note] Redis flashcard cache invalidation skipped: {inv_ex}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
