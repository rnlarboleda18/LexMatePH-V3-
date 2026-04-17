"""
Ingest structured LexCode/Codals/md/RPC.md into article_versions + rpc_codal (clean re-ingest).

Purpose: Phase 1 of the RPC pipeline — reset codal + version history from the base markdown,
before running LexCode/scripts/process_amendment.py for direct amendments.

Env: DB_CONNECTION_STRING (preferred) or api/local.settings.json Values.DB_CONNECTION_STRING.

Usage:
  python LexCode/scripts/ingest_rpc_base_from_md.py
  python LexCode/scripts/ingest_rpc_base_from_md.py --md-path LexCode/Codals/md/RPC.md --dry-run
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API = _REPO_ROOT / "api"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))

from codal_text import normalize_storage_markdown  # noqa: E402

_PIPE_DIR = Path(__file__).resolve().parent.parent / "pipelines" / "rpc"
_spec = importlib.util.spec_from_file_location(
    "rpc_md_stream_parser",
    _PIPE_DIR / "rpc_md_stream_parser.py",
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Cannot load rpc_md_stream_parser")
_rpc_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("rpc_md_stream_parser", _rpc_mod)
_spec.loader.exec_module(_rpc_mod)
parse_rpc_codex_md = _rpc_mod.parse_rpc_codex_md
chapter_num_from_chapter_heading = _rpc_mod.chapter_num_from_chapter_heading


def get_db_connection():
    conn_str = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if conn_str:
        import psycopg2

        return psycopg2.connect(conn_str)
    try:
        import psycopg2

        with open(_REPO_ROOT / "api" / "local.settings.json", encoding="utf-8") as f:
            conn_str = json.load(f)["Values"]["DB_CONNECTION_STRING"]
        return psycopg2.connect(conn_str)
    except Exception:
        import psycopg2

        raise SystemExit(
            "Set DB_CONNECTION_STRING or create api/local.settings.json with DB credentials."
        ) from None


def _rpc_codal_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rpc_codal'
        """
    )
    return {r[0] for r in cur.fetchall()}


def _structural_map_for_body(body: str) -> str:
    norm = normalize_storage_markdown(body or "")
    segs = [p for p in norm.split("\n\n") if p.strip()]
    m = [[0] for _ in segs] if segs else [[0]]
    return json.dumps(m)


def ingest(
    md_path: Path,
    *,
    dry_run: bool,
    wipe_rpc_links: bool,
) -> int:
    arts = parse_rpc_codex_md(md_path)
    if dry_run:
        print(f"[dry-run] Parsed {len(arts)} articles from {md_path}")
        return len(arts)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT code_id FROM legal_codes WHERE short_name = %s",
            ("RPC",),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO legal_codes (full_name, short_name, description)
                VALUES ('Revised Penal Code', 'RPC',
                        'The Revised Penal Code of the Philippines (Act No. 3815)')
                RETURNING code_id
                """
            )
            code_id = cur.fetchone()[0]
        else:
            code_id = row[0]

        if wipe_rpc_links:
            cur.execute(
                "DELETE FROM codal_case_links WHERE statute_id = %s",
                ("RPC",),
            )

        cur.execute("DELETE FROM article_versions WHERE code_id = %s", (code_id,))
        cur.execute("DELETE FROM rpc_codal")

        cols = _rpc_codal_columns(cur)

        av_batch = []
        for a in arts:
            norm_ver = normalize_storage_markdown(a.version_markdown)
            norm_body = normalize_storage_markdown(a.content_md)
            av_batch.append(
                (
                    code_id,
                    a.article_num,
                    norm_ver,
                    "1932-01-01",
                    None,
                    "Act No. 3815",
                )
            )

            merged_book = a.book_label_merged()
            merged_title = a.title_label_merged()
            merged_chapter = a.chapter_merged()

            row_dict: dict = {
                "article_title": a.article_title,
                "content_md": norm_body,
                "book": a.book,
                "title_num": a.title_num,
                "title_label": merged_title,
                "section_num": a.section_num,
                "section_label": a.section_label,
                "structural_map": _structural_map_for_body(norm_body),
            }
            anum_full = a.article_num
            if "article_suffix" in cols:
                m_hyp = re.match(r"^(\d+)-([A-Za-z]+)$", anum_full)
                if m_hyp:
                    row_dict["article_num"] = m_hyp.group(1)
                    row_dict["article_suffix"] = m_hyp.group(2)
                else:
                    row_dict["article_num"] = anum_full
                    row_dict["article_suffix"] = None
            else:
                row_dict["article_num"] = anum_full

            if "book_label" in cols:
                row_dict["book_label"] = merged_book
            if "chapter" in cols:
                row_dict["chapter"] = merged_chapter
            if "chapter_label" in cols:
                row_dict["chapter_label"] = merged_chapter
            if "chapter_num" in cols:
                row_dict["chapter_num"] = chapter_num_from_chapter_heading(a.chapter)
            if "amendments" in cols:
                row_dict["amendments"] = json.dumps([])

            insert_cols = [c for c in row_dict if c in cols]
            values = [row_dict[c] for c in insert_cols]
            col_sql = ", ".join(insert_cols)
            ph_parts = ["%s"] * len(values)
            if "created_at" in cols and "created_at" not in insert_cols:
                col_sql += ", created_at"
                ph_parts.append("NOW()")
            if "updated_at" in cols and "updated_at" not in insert_cols:
                col_sql += ", updated_at"
                ph_parts.append("NOW()")
            placeholders = ", ".join(ph_parts)
            cur.execute(
                f"INSERT INTO rpc_codal ({col_sql}) VALUES ({placeholders})",
                values,
            )

        if av_batch:
            from psycopg2.extras import execute_batch

            execute_batch(
                cur,
                """
                INSERT INTO article_versions
                (code_id, article_number, content, valid_from, valid_to, amendment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                av_batch,
            )

        conn.commit()
        print(f"Ingested {len(arts)} RPC articles into rpc_codal + article_versions (code_id={code_id}).")
        return len(arts)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description="Ingest base RPC.md into Postgres")
    p.add_argument(
        "--md-path",
        default=str(_REPO_ROOT / "LexCode" / "Codals" / "md" / "RPC.md"),
        help="Path to structured RPC.md",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--wipe-rpc-links",
        action="store_true",
        help="Also DELETE codal_case_links for statute_id=RPC (destructive).",
    )
    args = p.parse_args()
    md_path = Path(args.md_path)
    if not md_path.is_file():
        raise SystemExit(f"RPC markdown not found: {md_path}")
    ingest(md_path, dry_run=args.dry_run, wipe_rpc_links=args.wipe_rpc_links)


if __name__ == "__main__":
    main()
