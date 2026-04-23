#!/usr/bin/env python3
"""
Revert mistaken RPC article_versions rows for one or more amendment_id values,
repair the valid_from/valid_to chain, and rebuild rpc_codal content + amendments
JSON from the remaining history.

Purpose: Fix bad full-AI applies while keeping a truthful amendment trail.

Inputs (CLI):
  --amendment-id   Repeatable. e.g. "Republic Act No. 11648" (matches via _normalize_law_id)
  --articles       Comma-separated RPC article numbers (omit if using --discover-articles)
  --discover-articles  Query DB for every article_number that has a version with any listed amendment_id
  --code           legal_codes.short_name (default: RPC)
  --dry-run        Print planned actions; no DELETE/UPDATE

Modes:
  --mode ghost (default): delete only rows whose ``content`` matches the immediately
    prior version (AI "formal revision" / no-op). Preserves real RA 7659 penalty edits
    and real RA 11648 text changes (e.g. Arts. 266-A, 337, 338).
  --mode purge: delete every version row matching the amendment_id(s). Dangerous for
    RA 7659 — prefer ghost, or use --only-articles for a narrow fix.

Examples:
  python revert_rpc_amendment_versions.py --amendment-id "Republic Act No. 11648" \\
      --amendment-id "Republic Act No. 7659" --discover-articles --mode ghost

Environment:
  DB_CONNECTION_STRING preferred (cloud). Otherwise same fallbacks as process_amendment.get_db_connection.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_REPO / "api"))

from apply_amendment import _is_substantively_unchanged  # noqa: E402
from codal_text import normalize_storage_markdown  # noqa: E402
from process_amendment import (  # noqa: E402
    _normalize_law_id,
    get_db_connection,
    parse_article_title_body,
)


def _discover_affected_articles(cur, code_id, target_norms: set[str]) -> list[str]:
    cur.execute(
        """
        SELECT DISTINCT article_number, amendment_id
        FROM article_versions
        WHERE code_id = %s
        """,
        (code_id,),
    )
    found: set[str] = set()
    for art, aid in cur.fetchall():
        if _normalize_law_id(aid or "") in target_norms:
            found.add(str(art).strip())

    def sort_key(a: str):
        m = re.match(r"^(\d+)", a)
        if m:
            return (0, int(m.group(1)), a)
        return (1, 0, a)

    return sorted(found, key=sort_key)


def _repair_chain(cur, code_id: str, article_number: str) -> None:
    cur.execute(
        """
        SELECT version_id, valid_from
        FROM article_versions
        WHERE code_id = %s AND article_number = %s
        ORDER BY valid_from ASC
        """,
        (code_id, article_number),
    )
    rows = cur.fetchall()
    for i, (vid, _vf) in enumerate(rows):
        if i + 1 < len(rows):
            nxt = rows[i + 1][1]
            cur.execute(
                "UPDATE article_versions SET valid_to = %s WHERE version_id = %s",
                (nxt, vid),
            )
        else:
            cur.execute(
                "UPDATE article_versions SET valid_to = NULL WHERE version_id = %s",
                (vid,),
            )


def _rebuild_rpc_codal_row(cur, code_id: str, article_number: str) -> None:
    cur.execute(
        "SELECT id, article_title FROM rpc_codal WHERE article_num = %s",
        (article_number,),
    )
    meta = cur.fetchone()
    if not meta:
        print(f"    [WARN] No rpc_codal row for article {article_number}; skipped present view")
        return
    _rpc_id, existing_title = meta

    cur.execute(
        """
        SELECT amendment_id, valid_from, amendment_description, content
        FROM article_versions
        WHERE code_id = %s AND article_number = %s
        ORDER BY valid_from ASC
        """,
        (code_id, article_number),
    )
    hist = cur.fetchall()
    if not hist:
        print(f"    [WARN] No article_versions left for {article_number}")
        return

    cur.execute(
        """
        SELECT content FROM article_versions
        WHERE code_id = %s AND article_number = %s AND valid_to IS NULL
        LIMIT 1
        """,
        (code_id, article_number),
    )
    tip_row = cur.fetchone()
    if not tip_row:
        print(f"    [WARN] No open tip (valid_to IS NULL) for article {article_number}")
        return
    tip_content = tip_row[0]

    amendments: list[dict] = []
    for aid, vf, desc, _c in hist:
        if not aid:
            continue
        d = vf.isoformat() if hasattr(vf, "isoformat") else str(vf)
        amendments.append({"id": aid, "date": d[:10], "description": desc or ""})

    title, body = parse_article_title_body(tip_content)
    body = normalize_storage_markdown(body)
    if not title or title == "Unknown Title":
        title = existing_title or "Unknown Title"

    cur.execute(
        """
        UPDATE rpc_codal
        SET article_title = %s,
            content_md = %s,
            amendments = %s,
            updated_at = NOW()
        WHERE article_num = %s
        """,
        (title, body, json.dumps(amendments), article_number),
    )
    print(f"    [OK] rpc_codal rebuilt for article {article_number} ({len(amendments)} history entries)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Revert RPC article_versions + rebuild rpc_codal")
    parser.add_argument(
        "--amendment-id",
        action="append",
        dest="amendment_ids",
        required=True,
        help='Repeatable. e.g. "Republic Act No. 11648"',
    )
    parser.add_argument(
        "--articles",
        default=None,
        help="Comma-separated article_number values (required unless --discover-articles)",
    )
    parser.add_argument(
        "--discover-articles",
        action="store_true",
        help="Find all articles that have a version row for any listed --amendment-id",
    )
    parser.add_argument("--code", default="RPC", help="legal_codes.short_name")
    parser.add_argument(
        "--mode",
        choices=("ghost", "purge"),
        default="ghost",
        help="ghost: remove only no-op rows (default). purge: remove all rows for these amendment_id(s).",
    )
    parser.add_argument(
        "--skip-articles",
        default=None,
        help="Comma-separated article numbers to leave untouched entirely",
    )
    parser.add_argument(
        "--only-articles",
        default=None,
        help="If set, restrict to this comma-separated list (after discover or with --articles)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target_norms: set[str] = set()
    for raw in args.amendment_ids:
        n = _normalize_law_id(raw)
        if not n:
            print(f"Could not normalize --amendment-id {raw!r}")
            return 2
        target_norms.add(n)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (args.code,))
    row = cur.fetchone()
    if not row:
        print(f"No legal_codes row for short_name={args.code!r}")
        return 2
    code_id = row[0]

    if args.discover_articles:
        articles = _discover_affected_articles(cur, code_id, target_norms)
        print(f"Discovered {len(articles)} article(s) with version rows for: {args.amendment_ids}")
        if not articles:
            cur.close()
            conn.close()
            print("Nothing to revert.")
            return 0
    elif args.articles:
        articles = [a.strip() for a in args.articles.split(",") if a.strip()]
    else:
        cur.close()
        conn.close()
        print("Provide --discover-articles or --articles=...")
        return 2

    skip_set = {a.strip() for a in (args.skip_articles or "").split(",") if a.strip()}
    if args.only_articles:
        only = {a.strip() for a in args.only_articles.split(",") if a.strip()}
        articles = [a for a in articles if a in only]

    print(f"Mode: {args.mode}")

    for art in articles:
        print(f"\n=== Article {art} ===")
        if art in skip_set:
            print("  Skipped (--skip-articles).")
            continue
        cur.execute(
            """
            SELECT version_id, valid_from, valid_to, amendment_id, amendment_description, content
            FROM article_versions
            WHERE code_id = %s AND article_number = %s
            ORDER BY valid_from ASC
            """,
            (code_id, art),
        )
        ordered = cur.fetchall()
        bad_vids: list = []
        for i, row in enumerate(ordered):
            vid, vf, _vto, aid, desc, content = row
            if _normalize_law_id(aid or "") not in target_norms:
                continue
            if args.mode == "purge":
                bad_vids.append(vid)
                continue
            if i == 0:
                print(
                    f"  [skip] version_id={vid} is earliest row for article — cannot ghost-compare; use --mode purge for this article"
                )
                continue
            prev_content = ordered[i - 1][5]
            if _is_substantively_unchanged(prev_content, content):
                bad_vids.append(vid)
            else:
                print(
                    f"  [KEEP] version_id={vid} ({aid}, {vf}): content differs from prior — not a no-op row"
                )

        if not bad_vids:
            print("  No rows selected for removal; nothing to do.")
            continue
        print(f"  Remove {len(bad_vids)} version(s) ({args.mode}) for amendment_id(s): {args.amendment_ids!r}")
        if args.dry_run:
            bad_set = set(bad_vids)
            for v in ordered:
                if v[0] in bad_set:
                    print(f"    [dry-run] DELETE version_id={v[0]} valid_from={v[1]} desc_snip={(v[4] or '')[:80]!r}")
            print("    [dry-run] Would repair chain + rebuild rpc_codal")
            continue

        cur.execute(
            "DELETE FROM article_versions WHERE version_id IN %s",
            (tuple(bad_vids),),
        )
        _repair_chain(cur, code_id, art)
        _rebuild_rpc_codal_row(cur, code_id, art)

    if not args.dry_run:
        conn.commit()
        print("\nDone (committed).")
    else:
        conn.rollback()
        print("\nDry run complete (rolled back).")
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
