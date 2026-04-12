"""
Compare rows that share the same case_number in sc_decided_cases.

Usage (from repo root):
  python scripts/report_duplicate_case_numbers.py
  python scripts/report_duplicate_case_numbers.py --case "G.R. No. 88291"
  python scripts/report_duplicate_case_numbers.py --likely-dupes-only --limit 40

Connection: DB_CONNECTION_STRING env, else api/local.settings.json Values.DB_CONNECTION_STRING.

How to read the output
----------------------
* **Different `date` or `document_type`** — usually **different real dispositions**
  (main decision vs later resolutions). **Do not delete** these as "duplicates";
  your product should disambiguate by **id** and show date + type in search.

* **SUSPECT_DUPLICATE_PAIR** — same **date**, same **document_type**, same **body_md5**
  (PostgreSQL md5 of full_text_md). Same underlying document ingested twice with
  different **id**; digests may differ if the model re-ran.

Which id to delete (only for SUSPECT pairs — verify in UI first)
------------------------------------------------------------------
* Prefer **keeping** the row with **sc_url** set (canonical E-Library link), if only one has it.
* Else keep the row with **richer digests** (larger digest_facts_len + digest_significance_len).
* Else keep the **lower id** (older ingest) or **higher id** (newer pipeline) per your policy.
* Always re-check **foreign keys / playlists / logs** before DELETE.

This script is read-only; it does not delete anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Install psycopg2: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


LIGHT_SELECT = """
SELECT id,
       date::text AS date,
       case_number,
       document_type,
       short_title,
       sc_url,
       parent_id,
       ai_model,
       LENGTH(COALESCE(full_text_md, ''))::int AS full_text_md_len,
       md5(COALESCE(full_text_md, '')) AS body_md5,
       LENGTH(COALESCE(digest_facts, ''))::int AS digest_facts_len,
       LENGTH(COALESCE(digest_significance, ''))::int AS digest_significance_len
FROM sc_decided_cases
WHERE case_number = %s
ORDER BY id
"""


def load_conn_str() -> str:
    s = os.environ.get("DB_CONNECTION_STRING")
    if s:
        return s
    for path in ("api/local.settings.json", "local.settings.json"):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)["Values"]["DB_CONNECTION_STRING"]
        except OSError:
            continue
    print("Set DB_CONNECTION_STRING or add it to api/local.settings.json", file=sys.stderr)
    sys.exit(1)


def md5_hex(s: str | None) -> str | None:
    if not s:
        return None
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def body_md5(r: dict[str, Any]) -> str | None:
    return r.get("body_md5") or md5_hex(r.get("full_text_md"))


def row_summary(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id"],
        "date": str(r.get("date") or "")[:10],
        "document_type": r.get("document_type"),
        "short_title": (r.get("short_title") or "")[:80],
        "ai_model": (r.get("ai_model") or "")[:40],
        "sc_url": (r.get("sc_url") or "")[:100],
        "parent_id": r.get("parent_id"),
        "full_text_md_len": r.get("full_text_md_len") if "full_text_md_len" in r else len(r.get("full_text_md") or ""),
        "body_md5": body_md5(r),
        "digest_facts_len": r.get("digest_facts_len") if "digest_facts_len" in r else len(r.get("digest_facts") or ""),
        "digest_significance_len": r.get("digest_significance_len")
        if "digest_significance_len" in r
        else len(r.get("digest_significance") or ""),
    }


def classify_group(rows: list[dict[str, Any]]) -> str:
    if len(rows) < 2:
        return "SINGLE"
    dates = {str(r.get("date") or "")[:10] for r in rows}
    dtypes = {r.get("document_type") for r in rows}
    hashes = {h for r in rows if (h := body_md5(r))}
    if len(rows) >= 2 and len(hashes) == 1 and len(dates) == 1 and len(dtypes) == 1:
        return "SUSPECT_SAME_BODY_SAME_DATE_SAME_TYPE"
    if len(dates) > 1 or len(dtypes) > 1:
        return "LEGITIMATE_MULTI_DISPOSITION_SAME_DOCKET"
    return "REVIEW_MANUALLY_SAME_DATE_OR_TYPE"


def suspect_pairs(rows: list[dict[str, Any]]) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    n = len(rows)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = rows[i], rows[j]
            ha, hb = body_md5(a), body_md5(b)
            da = str(a.get("date") or "")[:10]
            db = str(b.get("date") or "")[:10]
            ta, tb = a.get("document_type"), b.get("document_type")
            if ha and ha == hb and da == db and ta == tb and a["id"] != b["id"]:
                reason = "identical body_md5 + same date + same document_type"
                out.append((min(a["id"], b["id"]), max(a["id"], b["id"]), reason))
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", help="Only this exact case_number string (e.g. 'G.R. No. 88291')")
    p.add_argument("--limit", type=int, default=25, help="Max duplicate groups to print in full")
    p.add_argument(
        "--likely-dupes-only",
        action="store_true",
        help="Only show groups where at least two rows share same date, document_type, and body_md5",
    )
    p.add_argument("--min-group-size", type=int, default=2, metavar="N")
    args = p.parse_args()

    conn = psycopg2.connect(load_conn_str())
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if args.case:
        cur.execute(LIGHT_SELECT, (args.case,))
        rows = cur.fetchall()
        if not rows:
            print(f"No rows for case_number = {args.case!r}")
            conn.close()
            return
        print(f"Group: {args.case!r}  ({len(rows)} row(s))\n")
        print("CLASSIFY:", classify_group(rows))
        for pair in suspect_pairs(rows):
            print(f"  SUSPECT_PAIR ids={pair[0]},{pair[1]} ({pair[2]})")
        print()
        for r in rows:
            print(json.dumps(row_summary(r), ensure_ascii=False, indent=2))
            print("---")
        conn.close()
        return

    cur.execute(
        """
        SELECT case_number, COUNT(*) AS n
        FROM sc_decided_cases
        WHERE case_number IS NOT NULL AND TRIM(case_number) <> ''
        GROUP BY case_number
        HAVING COUNT(*) >= %s
        ORDER BY n DESC, case_number
        """,
        (args.min_group_size,),
    )
    groups = cur.fetchall()
    print(f"Total duplicate case_number groups (size >= {args.min_group_size}): {len(groups)}\n")

    shown = 0
    suspect_group_count = 0
    for g in groups:
        cn = g["case_number"]
        cur.execute(LIGHT_SELECT, (cn,))
        rows = cur.fetchall()
        label = classify_group(rows)
        pairs = suspect_pairs(rows)

        if args.likely_dupes_only and not pairs:
            continue

        if shown >= args.limit:
            break

        suspect_group_count += 1 if pairs else 0
        print("=" * 88)
        print(f"case_number: {cn!r}  rows: {len(rows)}  CLASSIFY: {label}")
        if pairs:
            for lo, hi, reason in pairs:
                print(f"  >>> SUSPECT_DUPLICATE_PAIR: id {lo} vs {hi} -> {reason}")
        else:
            print("  (No identical body_md5 + same date + same type pairs in this group.)")
        print("  Per-row summary:")
        for r in rows:
            print("   ", json.dumps(row_summary(r), ensure_ascii=False))
        shown += 1

    conn.close()
    print()
    print(f"Printed {shown} group(s)." + (f" Of those, {suspect_group_count} had at least one suspect pair." if shown else ""))


if __name__ == "__main__":
    main()
