"""
Find sc_decided_cases rows that share the same *logical* docket set + same calendar date.

Grouping key:
  (docket_signature(case_number), date::date)

docket_signature:
  - Uppercase, collapse whitespace, normalize "G R" / stray spaces to "GR"
  - Collect 5+ digit docket numbers from the string
  - Sorted unique 5+ digit integers joined as "178034:178117:186984"
    (hyphenated pairs like 186984-85 contribute 186984 only; add 186985
    manually if your caption uses that form and rows fail to group.)

This catches punctuation/typo variants (semicolon vs comma; "G R." vs "G.R.")
for the same underlying G.R. bundle. It is not a legal parser; edge cases may
need manual review.

Usage (repo root):
  python scripts/list_duplicate_groups_case_number_date.py
  python scripts/list_duplicate_groups_case_number_date.py --out dup_groups.csv
  python scripts/list_duplicate_groups_case_number_date.py --min-rows 3

Connection: DB_CONNECTION_STRING or api/local.settings.json (read-only).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


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


def docket_signature(case_number: str) -> str:
    """Stable string key for 'same bundle of docket numbers' (typo-tolerant)."""
    if not case_number or not str(case_number).strip():
        return ""
    cn = str(case_number).strip().upper()
    cn = re.sub(r"\s+", " ", cn)
    cn = re.sub(r"G\s*R\s*", "GR", cn)

    nums: set[int] = set()

    def add_n(n: int) -> None:
        if n > 0:
            nums.add(n)

    # Plain docket numbers (G.R. / consolidated bundles are usually 5+ digits).
    # Deliberately no hyphen-range expansion here: patterns like 133586-603 are
    # not always "last two digits replaced" and would false-merge unrelated rows.
    for m in re.finditer(r"\d{5,}", cn):
        add_n(int(m.group(0)))

    if nums:
        return ":".join(str(n) for n in sorted(nums))

    # No 5+ digit tokens (e.g. some A.M. / short dockets). Collapsed alnum — treat
    # groups under this key as *weak*; they may collide across unrelated matters.
    fb = re.sub(r"[^A-Z0-9]+", "", cn)
    return fb or "EMPTY"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="Write CSV summary here (recommended; *.csv is gitignored at repo root)")
    ap.add_argument("--min-rows", type=int, default=2, help="Minimum rows in a group to report")
    ap.add_argument(
        "--print-groups",
        action="store_true",
        help="Print every duplicate group to stdout (default: summary only)",
    )
    args = ap.parse_args()

    conn = psycopg2.connect(conn_str())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT id,
               case_number,
               date::text AS date,
               document_type,
               LEFT(COALESCE(short_title, ''), 80) AS short_title,
               LENGTH(COALESCE(full_text_md, ''))::int AS body_len,
               md5(COALESCE(full_text_md, '')) AS body_md5,
               COALESCE(ai_model, '') AS ai_model
        FROM sc_decided_cases
        WHERE case_number IS NOT NULL AND TRIM(case_number) <> ''
        """
    )
    rows = cur.fetchall()
    conn.close()

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        sig = docket_signature(r["case_number"])
        d = str(r["date"] or "")[:10]
        if not sig or not d:
            continue
        groups[(sig, d)].append(dict(r))

    dupes = [(k, v) for k, v in groups.items() if len(v) >= args.min_rows]
    dupes.sort(key=lambda x: (-len(x[1]), x[0][1], x[0][0]))

    # Diagnostics: catch accidental mega-buckets
    sig_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        sig = docket_signature(r["case_number"])
        d = str(r["date"] or "")[:10]
        if sig and d:
            sig_counts[sig + "|" + d] += 1
    worst = sorted(sig_counts.items(), key=lambda x: -x[1])[:8]
    worst_line = " | ".join(f"{k} -> {v}" for k, v in worst)
    total_bucketed = sum(sig_counts.values())
    mx = max(sig_counts.values()) if sig_counts else 0

    print(f"Total rows scanned: {len(rows)}")
    print(f"Rows counted into buckets: {total_bucketed} (skipped {len(rows) - total_bucketed})")
    print(f"Max rows in one bucket: {mx}")
    print(f"Distinct (signature, date) keys: {len(groups)}")
    print(f"Keys with >= {args.min_rows} rows (duplicate groups): {len(dupes)}")
    print(f"Total rows sitting in those groups: {sum(len(v) for _, v in dupes)}")
    print(f"Largest buckets (signature|date=count): {worst_line}")

    writer = None
    fobj = None
    if args.out:
        fobj = open(args.out, "w", newline="", encoding="utf-8")
        writer = csv.writer(fobj)
        writer.writerow(
            [
                "docket_signature",
                "date",
                "n_rows",
                "n_distinct_body_md5",
                "ids",
                "case_numbers",
                "document_types",
            ]
        )

    for (sig, d), members in dupes:
        ids = [str(m["id"]) for m in members]
        cns = [m["case_number"] for m in members]
        dtypes = [str(m.get("document_type") or "") for m in members]
        md5s = {m["body_md5"] for m in members}
        if args.print_groups:
            line = (
                f"sig={sig} date={d} n={len(members)} distinct_body_md5={len(md5s)} "
                f"ids={','.join(ids)}"
            )
            print(line)
        if writer:
            writer.writerow(
                [
                    sig,
                    d,
                    len(members),
                    len(md5s),
                    ";".join(ids),
                    " | ".join(cns),
                    ";".join(dtypes),
                ]
            )

    if fobj:
        fobj.close()
        print(f"Wrote {args.out}")
    elif not args.print_groups:
        print("Tip: pass --out dup_groups_case_date.csv to save all groups, or --print-groups to list here.")


if __name__ == "__main__":
    main()
