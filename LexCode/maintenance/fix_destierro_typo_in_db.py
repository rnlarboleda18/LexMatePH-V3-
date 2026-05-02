#!/usr/bin/env python3
"""
Replace misspellings *Listierro* / *Lestierro* with *Destierro* / *destierro* (case-preserving)
in amendment-related database text — **not** from LexCode markdown sources.

Targets:
  - ``article_versions.content`` and ``article_versions.amendment_description`` (codal version history)
  - ``rpc_codal.content_md`` and string fields inside ``rpc_codal.amendments`` JSON
  - ``codal_amendments.description`` where ``statute_id = 'RPC'``

Usage:
  python fix_destierro_typo_in_db.py --dry-run
  python fix_destierro_typo_in_db.py --apply

Environment: ``DB_CONNECTION_STRING`` or ``api/local.settings.json`` (same as ``process_amendment``).
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

from process_amendment import get_db_connection  # noqa: E402

_TYPO_RE = re.compile(r"(?i)\bl(?:i|e)stierro\b")


def _fix_word(m: re.Match) -> str:
    w = m.group(0)
    if w.isupper():
        return "DESTIERRO"
    if w[0].isupper():
        return "Destierro"
    return "destierro"


def fix_text(s: str | None) -> tuple[str | None, bool]:
    if s is None or s == "":
        return s, False
    out = _TYPO_RE.sub(_fix_word, s)
    return out, out != s


def fix_json_values(obj):
    """Recursively fix strings in dict/list (e.g. rpc_codal.amendments)."""
    if isinstance(obj, str):
        new_s, _ = fix_text(obj)
        return new_s
    if isinstance(obj, list):
        return [fix_json_values(x) for x in obj]
    if isinstance(obj, dict):
        return {k: fix_json_values(v) for k, v in obj.items()}
    return obj


def main() -> None:
    ap = argparse.ArgumentParser(description="Fix Listierro/Lestierro → Destierro in DB (article_versions, rpc_codal, codal_amendments).")
    ap.add_argument("--apply", action="store_true", help="Write updates (default is dry-run).")
    args = ap.parse_args()
    dry_run = not args.apply

    conn = get_db_connection()
    cur = conn.cursor()
    total_updates = 0

    try:
        # --- article_versions ---
        cur.execute(
            """
            SELECT version_id, article_number, content, amendment_description
            FROM article_versions
            WHERE content ~* 'l[ie]stierro'
               OR COALESCE(amendment_description, '') ~* 'l[ie]stierro'
            """
        )
        av_rows = cur.fetchall()
        for version_id, article_number, content, amendment_description in av_rows:
            new_c, ch_c = fix_text(content)
            new_d, ch_d = fix_text(amendment_description)
            if not ch_c and not ch_d:
                continue
            print(f"article_versions version_id={version_id} article_number={article_number!r}")
            if dry_run:
                total_updates += 1
                continue
            cur.execute(
                """
                UPDATE article_versions
                SET content = %s, amendment_description = %s
                WHERE version_id = %s
                """,
                (new_c, new_d, version_id),
            )
            total_updates += cur.rowcount

        # --- rpc_codal ---
        cur.execute(
            """
            SELECT id, article_num, content_md, amendments
            FROM rpc_codal
            WHERE content_md ~* 'l[ie]stierro'
               OR amendments::text ~* 'l[ie]stierro'
            """
        )
        rpc_rows = cur.fetchall()
        for row_id, article_num, content_md, amendments in rpc_rows:
            new_md, ch_md = fix_text(content_md)
            new_am = None
            ch_am = False
            if amendments is not None:
                new_am = fix_json_values(amendments)
                ch_am = json.dumps(new_am, sort_keys=True, default=str) != json.dumps(
                    amendments, sort_keys=True, default=str
                )
            if not ch_md and not ch_am:
                continue
            print(f"rpc_codal id={row_id} article_num={article_num!r}")
            if dry_run:
                total_updates += 1
                continue
            cur.execute(
                """
                UPDATE rpc_codal
                SET content_md = %s, amendments = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (new_md, new_am if amendments is not None else amendments, row_id),
            )
            total_updates += cur.rowcount

        # --- codal_amendments (RPC) ---
        cur.execute(
            """
            SELECT id, provision_id, amendment_law, description
            FROM codal_amendments
            WHERE statute_id = 'RPC'
              AND description IS NOT NULL
              AND description ~* 'l[ie]stierro'
            """
        )
        ca_rows = cur.fetchall()
        for ca_id, provision_id, amendment_law, desc in ca_rows:
            new_desc, ch = fix_text(desc)
            if not ch:
                continue
            print(f"codal_amendments id={ca_id} provision_id={provision_id!r} law={amendment_law!r}")
            if dry_run:
                total_updates += 1
                continue
            cur.execute(
                "UPDATE codal_amendments SET description = %s WHERE id = %s",
                (new_desc, ca_id),
            )
            total_updates += cur.rowcount

        if dry_run:
            print(f"\n[dry-run] Would touch {total_updates} row(s). Re-run with --apply to write.")
        else:
            conn.commit()
            print(f"\n[apply] Committed updates affecting {total_updates} row operation(s).")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
