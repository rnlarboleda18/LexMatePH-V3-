"""
Load baseline RPC text from ``LexCode/Codals/md/RPC.md`` into ``article_versions``
and ``rpc_codal`` (structural columns + ``content_md``), using the same stream
parser as the rest of the LexCode RPC toolchain.

Intended as **phase 1** of ``scripts/reingest_rpc_pipeline.py`` and
``scripts/reingest_rpc_manual_pipeline.py``.

Preserves ``article_versions`` row(s) for article number ``0`` (preamble), if any,
since ``RPC.md`` does not emit a ``##### Article 0`` block.

By default, deletes ``rpc_codal`` rows whose ``article_num`` does not appear in the
parsed ``RPC.md`` (e.g. articles introduced only by amendatory laws). Use
``--keep-orphan-rpc-rows`` to retain them.

Environment: ``DB_CONNECTION_STRING`` or ``api/local.settings.json`` (same as
``process_amendment.py``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_API = _REPO / "api"
_PIPE = _REPO / "LexCode" / "pipelines"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))

import psycopg2

from codal_text import normalize_storage_markdown
from rpc.rpc_md_stream_parser import (
    RpcArticleRecord,
    chapter_num_from_chapter_heading,
    parse_rpc_codex_md,
)

_DEFAULT_MD = _REPO / "LexCode" / "Codals" / "md" / "RPC.md"
_BASELINE_AMENDMENT_ID = "Act No. 3815"
_BASELINE_DATE = "1932-01-01"
_BASELINE_DESC = "Revised Penal Code baseline ingested from RPC.md"


def get_db_connection():
    conn_str = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if conn_str:
        return psycopg2.connect(conn_str)
    api_settings = _REPO / "api" / "local.settings.json"
    try:
        with open(api_settings, encoding="utf-8") as f:
            conn_str = json.load(f)["Values"]["DB_CONNECTION_STRING"]
    except Exception:
        conn_str = (
            "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@"
            "localhost:5432/lexmateph-ea-db"
        )
    return psycopg2.connect(conn_str)


def _rpc_code_id(cur) -> str:
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC' LIMIT 1")
    row = cur.fetchone()
    if not row:
        raise RuntimeError("legal_codes has no row with short_name = 'RPC'")
    return str(row[0])


def _row_struct(rec: RpcArticleRecord) -> tuple:
    chapter_label = rec.chapter_merged()
    chapter_num = chapter_num_from_chapter_heading(rec.chapter)
    return (
        rec.article_title,
        normalize_storage_markdown(rec.content_md),
        rec.book,
        rec.book_label_merged(),
        rec.title_num,
        rec.title_label_merged(),
        chapter_label,
        chapter_num,
        rec.section_num,
        rec.section_label,
        rec.article_num,
    )


def _upsert_rpc_codal(cur, rec: RpcArticleRecord) -> None:
    t = _row_struct(rec)
    cur.execute(
        """
        UPDATE rpc_codal
        SET article_title = %s,
            content_md = %s,
            book = %s,
            book_label = %s,
            title_num = %s,
            title_label = %s,
            chapter_label = %s,
            chapter_num = %s,
            section_num = %s,
            section_label = %s,
            amendments = '[]'::jsonb,
            structural_map = '[]'::jsonb,
            updated_at = NOW()
        WHERE article_num = %s
        """,
        t,
    )
    if cur.rowcount:
        return
    cur.execute(
        """
        INSERT INTO rpc_codal
        (article_num, article_title, content_md, amendments,
         book, book_label, title_num, title_label, chapter_label, chapter_num,
         section_label, section_num, created_at, updated_at)
        VALUES (%s, %s, %s, '[]'::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (
            rec.article_num,
            rec.article_title,
            normalize_storage_markdown(rec.content_md),
            rec.book,
            rec.book_label_merged(),
            rec.title_num,
            rec.title_label_merged(),
            rec.chapter_merged(),
            chapter_num_from_chapter_heading(rec.chapter),
            rec.section_label,
            rec.section_num,
        ),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest RPC.md baseline into Postgres")
    ap.add_argument(
        "--md-path",
        type=Path,
        default=_DEFAULT_MD,
        help=f"Path to RPC markdown (default: {_DEFAULT_MD})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse RPC.md and print summary only; no database access",
    )
    ap.add_argument(
        "--wipe-rpc-links",
        action="store_true",
        help="DELETE codal_case_links rows with statute_id = 'RPC' before ingest",
    )
    ap.add_argument(
        "--keep-orphan-rpc-rows",
        action="store_true",
        help=(
            "Keep rpc_codal rows whose article_num is not in RPC.md (e.g. 134-A from a prior run). "
            "Default: delete those rows so amendments can re-insert them."
        ),
    )
    args = ap.parse_args()
    md_path = args.md_path.resolve()
    if not md_path.is_file():
        sys.exit(f"RPC markdown not found: {md_path}")

    records = parse_rpc_codex_md(md_path)
    nums = [r.article_num for r in records]
    print(f"Parsed {len(records)} articles from {md_path}")

    if args.dry_run:
        print("[dry-run] Skipping database writes.")
        print(f"  First: Article {nums[0]!r}, last: Article {nums[-1]!r}")
        return

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if args.wipe_rpc_links:
            cur.execute("DELETE FROM codal_case_links WHERE statute_id = 'RPC'")
            print(f"[wipe-rpc-links] Deleted {cur.rowcount} codal_case_links rows.")

        code_id = _rpc_code_id(cur)

        cur.execute(
            """
            DELETE FROM article_versions
            WHERE code_id = %s AND article_number <> '0'
            """,
            (code_id,),
        )
        print(f"Deleted {cur.rowcount} article_versions rows (RPC, except article 0).")

        allowed_article_nums = tuple({str(r.article_num) for r in records})
        if not args.keep_orphan_rpc_rows:
            cur.execute(
                """
                DELETE FROM rpc_codal
                WHERE CAST(article_num AS TEXT) NOT IN %s
                """,
                (allowed_article_nums,),
            )
            print(f"Deleted {cur.rowcount} orphan rpc_codal rows (article_num not present in RPC.md).")

        cur.execute(
            """
            UPDATE rpc_codal
            SET amendments = '[]'::jsonb,
                structural_map = '[]'::jsonb
            """
        )
        print(f"Reset amendments/structural_map on {cur.rowcount} rpc_codal rows.")

        for i, rec in enumerate(records, start=1):
            _upsert_rpc_codal(cur, rec)
            content = normalize_storage_markdown(rec.version_markdown)
            cur.execute(
                """
                INSERT INTO article_versions
                (code_id, article_number, content, valid_from, valid_to,
                 amendment_id, amendment_description)
                VALUES (%s, %s, %s, %s, NULL, %s, %s)
                """,
                (
                    code_id,
                    rec.article_num,
                    content,
                    _BASELINE_DATE,
                    _BASELINE_AMENDMENT_ID,
                    _BASELINE_DESC,
                ),
            )
            if i % 100 == 0:
                print(f"  ... {i}/{len(records)} articles")

        conn.commit()
        print(f"Ingest complete: {len(records)} articles written.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
