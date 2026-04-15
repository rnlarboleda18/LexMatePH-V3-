"""
One-off repair: RPC Article 125 in `rpc_codal.content_md`.

Root cause: Executive Order No. 272 (1987) Sec. 1 quotes the amendatory text in straight
double quotes (see `LexCode/Codals/md/eo_272_1987.md`). Some ingest paths copied that
literal quoted block into the codal row. Amendment metadata can still correctly cite EO 272
while the stored body keeps the quote wrapper.

This script sets `content_md` to the EO 272 amendatory substance **without** the outer `"` … `"`,
and **without** a leading `Art. 125. Delay…` sentence so the stream header is not duplicated in the body
(body begins at *The penalties provided in the next preceding article…*).

Inputs:
  - `DB_CONNECTION_STRING` (preferred), or `api/local.settings.json` → Values.DB_CONNECTION_STRING

Usage:
  python scripts/fix_rpc_article_125_eo272_content.py          # dry-run: print match + preview
  python scripts/fix_rpc_article_125_eo272_content.py --apply    # commit UPDATE

Do not re-run after the row is corrected unless you intentionally need to reset the body.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
_API_DIR = os.path.join(_REPO_ROOT, "api")

# EO 272 Sec. 1 substance: no outer quotes; no "Art. 125. Delay…" lead (LexCode already shows article title).
ARTICLE_125_BODY_MD = (
    "The penalties provided in the next preceding article shall be imposed upon the public officer or employee "
    "who shall detain any person for some legal ground and shall fail to deliver such person to the proper "
    "judicial authorities within the period of twelve (12) hours, for crimes or offenses punishable by light "
    "penalties, or their equivalent; eighteen (18) hours, for crimes or offenses punishable by correctional "
    "penalties, or their equivalent, and thirty-six (36) hours, for crimes or offenses punishable by afflictive "
    "or capital penalties, or their equivalent.\n\n"
    "In every case, the person detained shall be informed of the caused of his detention and shall be allowed, "
    "upon his request, to communicate and confer at any time with his attorney or counsel."
)


def _connection_string() -> str:
    s = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if s:
        return s
    path = os.path.join(_API_DIR, "local.settings.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["Values"]["DB_CONNECTION_STRING"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform UPDATE and commit (default is dry-run).",
    )
    args = parser.parse_args()

    try:
        conn_str = _connection_string()
    except Exception as e:
        print(f"Could not load DB connection string: {e}", file=sys.stderr)
        return 1

    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT id, book, article_num, LEFT(content_md, 120) AS head,
               LENGTH(content_md) AS len_md
        FROM rpc_codal
        WHERE CAST(article_num AS TEXT) = '125'
        ORDER BY book NULLS LAST, id
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("No rpc_codal row with article_num = 125.")
        cur.close()
        conn.close()
        return 1

    for r in rows:
        print(
            f"id={r['id']} book={r['book']} article_num={r['article_num']!r} len={r['len_md']}\n"
            f"  head: {r['head']!r}\n"
        )

    if not args.apply:
        print("Dry-run only. Re-run with --apply to set content_md (EO 272 body from penalties paragraph).")
        cur.close()
        conn.close()
        return 0

    upd = conn.cursor()
    try:
        upd.execute(
            """
            UPDATE rpc_codal
            SET content_md = %s, updated_at = NOW()
            WHERE CAST(article_num AS TEXT) = '125'
            """,
            (ARTICLE_125_BODY_MD,),
        )
    except Exception:
        conn.rollback()
        upd.execute(
            "UPDATE rpc_codal SET content_md = %s WHERE CAST(article_num AS TEXT) = '125'",
            (ARTICLE_125_BODY_MD,),
        )

    n = upd.rowcount
    conn.commit()
    upd.close()
    cur.close()
    conn.close()
    print(f"Updated {n} row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
