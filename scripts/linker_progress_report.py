"""Print RPC/RCC codal linker backlog by decision year (matches unified_codal_linker filters)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2

root = Path(__file__).resolve().parent.parent


def _db_url() -> str:
    vals = json.loads((root / "api" / "local.settings.json").read_text(encoding="utf-8")).get(
        "Values"
    ) or {}
    db = (os.environ.get("DB_CONNECTION_STRING") or vals.get("DB_CONNECTION_STRING") or "").strip()
    if not db:
        sys.exit("Set DB_CONNECTION_STRING or add it to api/local.settings.json Values.")
    return db


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report linker backlog: cases with digests but no RPC/RCC codal_case_links row."
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=2019,
        help="First decision year (inclusive). Default: 2019",
    )
    parser.add_argument(
        "--to-year",
        type=int,
        default=2025,
        help="Last decision year (inclusive). Default: 2025",
    )
    args = parser.parse_args()
    if args.from_year > args.to_year:
        sys.exit("--from-year must be <= --to-year")

    conn = psycopg2.connect(_db_url())
    cur = conn.cursor()
    print(
        "year | decided | with_RPC_or_RCC_link | pending (digest, no RPC/RCC link)\n"
        "-----|---------|----------------------|-----------------------------------"
    )
    for y in range(args.from_year, args.to_year + 1):
        cur.execute(
            """
            SELECT COUNT(*) FROM sc_decided_cases s
            WHERE s.date >= %s AND s.date <= %s
            """,
            (f"{y}-01-01", f"{y}-12-31"),
        )
        decided = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(DISTINCT l.case_id)
            FROM codal_case_links l
            JOIN sc_decided_cases s ON s.id = l.case_id
            WHERE UPPER(TRIM(l.statute_id::text)) IN ('RPC', 'RCC')
              AND s.date >= %s AND s.date <= %s
            """,
            (f"{y}-01-01", f"{y}-12-31"),
        )
        linked = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM sc_decided_cases s
            WHERE (main_doctrine IS NOT NULL
                   OR digest_ruling IS NOT NULL
                   OR digest_ratio IS NOT NULL
                   OR digest_issues IS NOT NULL)
              AND s.date >= %s AND s.date <= %s
              AND NOT EXISTS (
                SELECT 1 FROM codal_case_links l
                WHERE l.case_id = s.id
                  AND UPPER(TRIM(l.statute_id::text)) IN ('RPC', 'RCC')
              )
            """,
            (f"{y}-01-01", f"{y}-12-31"),
        )
        pending = cur.fetchone()[0]
        pct = (100.0 * linked / decided) if decided else 0.0
        print(f"{y:4} | {decided:7} | {linked:20} | {pending:5}  ({pct:.1f}% of year have link)")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
