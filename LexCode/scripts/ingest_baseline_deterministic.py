"""
**1932 baseline** ingestion for the RPC: deterministic parse of ``RPC.md`` (no AI).

Uses ``rpc_md_stream_parser.parse_rpc_codex_md`` so **Book / Title / Chapter / Section**
metadata is written to ``rpc_codal``. The LexCode stream hoists ``section_label`` (and peers)
into visible headers; the previous regex-only path left those columns null.

Seeds ``article_versions`` (``BASELINE_1932``) and updates ``rpc_codal`` — part of the audit trail
(see ``process_amendment.apply_amendment_to_database``).
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import psycopg2

# Setup environment
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "api"))
from codal_text import normalize_storage_markdown

from deterministic_lexcode import DEFAULT_RPC_BASELINE_PATH

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


def _structural_map_for_body(body: str) -> str:
    norm = normalize_storage_markdown(body or "")
    segs = [p for p in norm.split("\n\n") if p.strip()]
    m = [[0] for _ in segs] if segs else [[0]]
    return json.dumps(m)


def _rpc_codal_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rpc_codal'
        """
    )
    return {r[0] for r in cur.fetchall()}


def get_db_connection():
    api_settings = _REPO_ROOT / "api" / "local.settings.json"
    try:
        with open(api_settings, encoding="utf-8") as f:
            conn_str = json.load(f)["Values"]["DB_CONNECTION_STRING"]
    except Exception:
        conn_str = os.environ.get("DB_CONNECTION_STRING")
    return psycopg2.connect(conn_str)


def _row_dict_for_rpc_codal(a, cols: set[str]) -> dict:
    """Mirror LexCode/scripts/ingest_rpc_base_from_md.py mapping."""
    norm_body = normalize_storage_markdown(a.content_md)
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

    return {k: v for k, v in row_dict.items() if k in cols}


def _upsert_rpc_codal_row(cur, row_dict: dict, cols: set[str]) -> None:
    """INSERT or UPDATE one rpc_codal row (same column set as ingest_rpc_base_from_md)."""
    lookup_num = row_dict["article_num"]
    cur.execute("SELECT id FROM rpc_codal WHERE article_num = %s", (lookup_num,))
    exists = cur.fetchone()

    if exists:
        set_keys = [k for k in row_dict if k != "article_num"]
        if not set_keys:
            return
        set_clause = ", ".join(f"{k} = %s" for k in set_keys)
        vals = [row_dict[k] for k in set_keys] + [lookup_num]
        cur.execute(
            f"UPDATE rpc_codal SET {set_clause}, updated_at = NOW() WHERE article_num = %s",
            vals,
        )
        return

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


def ingest_baseline():
    baseline_path = DEFAULT_RPC_BASELINE_PATH
    if not baseline_path.exists():
        print("ERROR: RPC.md not found")
        return

    print(f"Parsing baseline {baseline_path.name} (stream parser with Book/Title/Chapter/Section)...")
    arts = parse_rpc_codex_md(baseline_path)
    print(f"Found {len(arts)} articles.")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        amendment_id = "BASELINE_1932"
        date = "1932-01-01"
        cols = _rpc_codal_columns(cur)

        for a in arts:
            norm_ver = normalize_storage_markdown(a.version_markdown)
            anum = a.article_num

            cur.execute(
                """
                SELECT version_id FROM article_versions
                WHERE article_number = %s
                AND amendment_id = %s
                AND code_id = (SELECT code_id FROM legal_codes WHERE full_name ILIKE '%%Revised Penal Code%%' LIMIT 1)
                """,
                (anum, amendment_id),
            )
            if cur.fetchone():
                cur.execute(
                    """
                    UPDATE article_versions
                    SET content = %s
                    WHERE article_number = %s AND amendment_id = %s
                    AND code_id = (SELECT code_id FROM legal_codes WHERE full_name ILIKE '%%Revised Penal Code%%' LIMIT 1)
                    """,
                    (norm_ver, anum, amendment_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO article_versions
                    (code_id, article_number, content, valid_from, amendment_id)
                    VALUES ((SELECT code_id FROM legal_codes WHERE full_name ILIKE '%%Revised Penal Code%%' LIMIT 1), %s, %s, %s, %s)
                    """,
                    (anum, norm_ver, date, amendment_id),
                )

            row_dict = _row_dict_for_rpc_codal(a, cols)
            _upsert_rpc_codal_row(cur, row_dict, cols)

        conn.commit()
        print("Successfully ingested 1932 baseline (with structural headers for codal stream).")
    except Exception as e:
        conn.rollback()
        print(f"CRITICAL ERROR: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    ingest_baseline()
