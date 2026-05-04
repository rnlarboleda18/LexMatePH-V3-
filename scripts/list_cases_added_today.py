"""
List rows in cloud ``sc_decided_cases`` whose ``created_at`` falls on today's
calendar date in UTC (default) or Asia/Manila.

Compares instant-based timestamps consistently with Postgres using
``(created_at AT TIME ZONE zone)::date`` (works with ``timestamp with time
zone``; if the column is naive UTC wall-clock from ``NOW()``, PostgreSQL treats
``AT TIME ZONE 'UTC'`` as that UTC instant).

Reads ``DB_CONNECTION_STRING`` from ``api/local.settings.json`` (or repo root
``local.settings.json`` merged by ``load_api_local_settings_into_environ``).

Usage::
  python scripts/list_cases_added_today.py [--tz utc|manila]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from load_local_settings_env import load_api_local_settings_into_environ

_ZONE = {"utc": "UTC", "manila": "Asia/Manila"}


def main() -> None:
    parser = argparse.ArgumentParser(description="List sc_decided_cases inserted on today's calendar date.")
    parser.add_argument(
        "--tz",
        choices=("utc", "manila"),
        default="utc",
        help="Calendar zone for midnight boundary (default: utc).",
    )
    args = parser.parse_args()

    load_api_local_settings_into_environ(_REPO)
    cs = os.environ.get("DB_CONNECTION_STRING")
    if not cs:
        print("DB_CONNECTION_STRING is not set (api/local.settings.json Values).")
        sys.exit(1)

    zone = _ZONE[args.tz]

    conn = psycopg2.connect(cs)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT pg_typeof(created_at) AS created_at_type FROM sc_decided_cases LIMIT 1
                """,
            )
            trow = cur.fetchone()

            cur.execute(
                """
                SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::date AS ph_today,
                       (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date AS utc_today,
                       CURRENT_TIMESTAMP AS db_now
                """,
            )
            bounds = cur.fetchone()
            ctype = ""
            if isinstance(trow, dict):
                v = trow.get("created_at_type")
            elif trow is not None and len(trow) > 0:
                v = trow[0]
            else:
                v = None
            ctype = str(v)

            naive = "without time zone" in ctype.lower()

            if zone == "UTC":
                day_expr = "(created_at AT TIME ZONE 'UTC')::date"
                cmp_expr = "(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date"
            elif naive:
                day_expr = "((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Manila')::date"
                cmp_expr = "(CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::date"
            else:
                day_expr = "(created_at AT TIME ZONE 'Asia/Manila')::date"
                cmp_expr = "(CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::date"

            sql = f"""
                SELECT id, created_at, case_number, short_title, full_title, date,
                       sc_url, scrape_source
                  FROM sc_decided_cases
                 WHERE {day_expr} = {cmp_expr}
                 ORDER BY created_at ASC, id ASC
            """
            cur.execute(sql)
            rows = cur.fetchall()

        assert bounds is not None
        print(f"created_at PostgreSQL type: {ctype}")
        print(f"Database now(): {bounds['db_now']}")
        print(f"Today's date (Asia/Manila): {bounds['ph_today']}")
        print(f"Today's date (UTC):         {bounds['utc_today']}")
        print(f"\nWHERE {day_expr}\n      = {cmp_expr}\n")
        print(f"Matching rows: {len(rows)}\n")

        if not rows:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, created_at, case_number, short_title
                      FROM sc_decided_cases
                     WHERE created AT >= (CURRENT_TIMESTAMP - interval '96 hours')
                     ORDER BY created_at DESC
                     LIMIT 20
                    """.replace("created AT", "created_at"),
                )
                recent = cur.fetchall()
            if recent:
                lbl = bounds["utc_today"] if zone == "UTC" else bounds["ph_today"]
                print(
                    f"(Zero matches for today's {zone} date.) Recent inserts within 96 h "
                    f"(db_max ~ {lbl}):\n",
                )
                for rr in recent:
                    st = rr.get("short_title") or ""
                    snip = (st[:60] + "…") if len(st) > 60 else st
                    print(f"  {rr['id']!s:>8}  {rr['created_at']}  {rr['case_number']!r}  {snip!r}")
            return

        for r in rows:
            st = (r.get("short_title") or "").strip()
            ft = (r.get("full_title") or "").strip()
            line = st or ft or ""
            t80 = line[:80] + ("…" if len(line) > 80 else "")
            print(f"id={r['id']}  created_at={r['created_at']}")
            print(f"  case_number={r['case_number']!r}  decision_date={r['date']}")
            print(f"  short/full title: {t80!r}")
            print(f"  sc_url={r['sc_url']}")
            print(f"  scrape_source={r['scrape_source']!r}")
            print()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
