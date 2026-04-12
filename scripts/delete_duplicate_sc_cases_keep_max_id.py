"""
Delete duplicate sc_decided_cases rows identified by the same logic as
list_duplicate_groups_case_number_date.py: (docket_signature(case_number), date).

Keeps the row with the **highest id** in each group; deletes all others.

Before DELETE:
  - Repoints sc_decided_cases.parent_id and any FK references from other tables
    to the keeper id (so deletes do not violate constraints).

Usage (repo root):
  python scripts/delete_duplicate_sc_cases_keep_max_id.py          # plan only
  python scripts/delete_duplicate_sc_cases_keep_max_id.py --execute

Connection: DB_CONNECTION_STRING or api/local.settings.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from list_duplicate_groups_case_number_date import docket_signature  # noqa: E402


def conn_str() -> str:
    if os.environ.get("DB_CONNECTION_STRING"):
        return os.environ["DB_CONNECTION_STRING"]
    for p in ("api/local.settings.json", "local.settings.json"):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)["Values"]["DB_CONNECTION_STRING"]
        except OSError:
            continue
    sys.exit("No DB connection configured.")


def fk_refs_to_sc_decided_cases(cur) -> list[tuple[str, str]]:
    """(table_name, column_name) referencing public.sc_decided_cases(id)."""
    cur.execute(
        """
        SELECT DISTINCT c.conrelid::regclass::text AS tbl, a.attname AS col
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
        WHERE c.contype = 'f'
          AND c.confrelid = to_regclass('public.sc_decided_cases')
        ORDER BY 1, 2
        """
    )
    out = []
    for row in cur.fetchall():
        t = row["tbl"] if isinstance(row, dict) else row[0]
        col = row["col"] if isinstance(row, dict) else row[1]
        t = t.strip('"')
        out.append((t, col))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true", help="Apply repoint + DELETE (default: plan only)")
    args = ap.parse_args()

    conn = psycopg2.connect(conn_str())
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT id, case_number, date::text AS date
        FROM sc_decided_cases
        WHERE case_number IS NOT NULL AND TRIM(case_number) <> ''
        """
    )
    rows = cur.fetchall()

    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in rows:
        sig = docket_signature(r["case_number"])
        d = str(r["date"] or "")[:10]
        if not sig or not d:
            continue
        groups[(sig, d)].append(int(r["id"]))

    delete_ids: list[int] = []
    old_to_keep: dict[int, int] = {}
    for (_sig, _d), ids in groups.items():
        if len(ids) < 2:
            continue
        keep = max(ids)
        for i in ids:
            if i != keep:
                delete_ids.append(i)
                old_to_keep[i] = keep

    delete_ids.sort()
    print(f"Duplicate groups (>=2 rows): {sum(1 for v in groups.values() if len(v) >= 2)}")
    print(f"Rows to delete (lower ids): {len(delete_ids)}")

    if not delete_ids:
        conn.close()
        return

    fks = fk_refs_to_sc_decided_cases(cur)
    print(f"FK references into sc_decided_cases(id): {len(fks)}")
    for t, c in fks:
        print(f"  {t}.{c}")

    if not args.execute:
        print("Plan only (no writes). Pass --execute to apply repoint + DELETE.")
        conn.close()
        return

    # --execute
    cur2 = conn.cursor()
    try:
        cur2.execute("BEGIN")

        vals = ",".join(
            cur2.mogrify("(%s,%s)", (o, n)).decode() for o, n in old_to_keep.items()
        )

        # Repoint self-reference first
        cur2.execute(
            f"""
            UPDATE public.sc_decided_cases t
            SET parent_id = m.new_id
            FROM (VALUES {vals}) AS m(old_id, new_id)
            WHERE t.parent_id = m.old_id
            """
        )
        print(f"Updated sc_decided_cases.parent_id rows affected: {cur2.rowcount}")

        for tbl, col in fks:
            if "sc_decided_cases" in tbl and col == "parent_id":
                continue
            cur2.execute(
                f"""
                UPDATE {tbl} t
                SET {col} = m.new_id
                FROM (VALUES {vals}) AS m(old_id, new_id)
                WHERE t.{col} = m.old_id
                """
            )
            if cur2.rowcount:
                print(f"Updated {tbl}.{col}: {cur2.rowcount} rows")

        cur2.execute(
            "DELETE FROM sc_decided_cases WHERE id = ANY(%s)",
            (delete_ids,),
        )
        print(f"Deleted from sc_decided_cases: {cur2.rowcount} rows")

        cur2.execute("COMMIT")
    except Exception as e:
        cur2.execute("ROLLBACK")
        print(f"Rolled back: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
