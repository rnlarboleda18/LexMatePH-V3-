"""
First occurrence of each structural label in codal *reading order* (article_num),
not MIN(primary key) — UUID ordering does not follow the code sequence.
Used by LexPlay TTS header assembly and RPC precache.

Label keys are whitespace-normalized so "Title IX:  Foo" and "Title IX: Foo" share
one partition — otherwise each chapter block can look like a new title and Title is
re-announced at every chapter boundary.
"""

from __future__ import annotations

import re

# Strip non-digits for numeric sort; tie-break on full article_num string.
_CODAL_ART_ORDER_SQL = (
    "CAST(NULLIF(REGEXP_REPLACE(TRIM(COALESCE(article_num::text, '')), '[^0-9]', '', 'g'), '') AS INTEGER) "
    "NULLS LAST, TRIM(COALESCE(article_num::text, '')) ASC NULLS LAST"
)

# SQL expr: collapse internal whitespace for stable PARTITION BY / lookup keys (must match normalize_codal_label_key).
# Use POSIX [[:space:]] — E'\s+' misparses in some PG versions, treating \s as literal 's'.
_LABEL_KEY_SQL = "LOWER(TRIM(REGEXP_REPLACE(TRIM({col}), '[[:space:]]+', ' ', 'g')))"


def normalize_codal_label_key(label: str) -> str:
    """Same normalization as fetch_codal_family_bounds map keys (for Python-side lookups)."""
    s = (label or "").strip()
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).lower()


def _partition_first_label_ids(cur, table: str, column: str) -> dict[str, str]:
    key_expr = _LABEL_KEY_SQL.format(col=column)
    q = f"""
    WITH ranked AS (
      SELECT id,
        {key_expr} AS lk,
        ROW_NUMBER() OVER (
          PARTITION BY {key_expr}
          ORDER BY {_CODAL_ART_ORDER_SQL}
        ) AS rn
      FROM {table}
      WHERE {column} IS NOT NULL AND TRIM({column}) <> ''
    )
    SELECT lk, id FROM ranked WHERE rn = 1
    """
    cur.execute(q)
    return {r[0]: str(r[1]) for r in cur.fetchall()}


def _partition_first_book_ids(cur, table: str) -> dict[str, str]:
    q = f"""
    WITH ranked AS (
      SELECT id, book::text AS bk,
        ROW_NUMBER() OVER (
          PARTITION BY book
          ORDER BY {_CODAL_ART_ORDER_SQL}
        ) AS rn
      FROM {table}
      WHERE book IS NOT NULL
    )
    SELECT bk, id FROM ranked WHERE rn = 1
    """
    cur.execute(q)
    return {str(r[0]): str(r[1]) for r in cur.fetchall()}


def _partition_title_start_by_book_and_num(cur, table: str) -> dict[str, str]:
    """
    First row id per (book, title_num) in codal order.
    Key: "{book}|{title_num}" with COALESCE(TRIM(book::text), '') to match Python lookups.
    Stops Title from re-announcing when chapter rows use different title_label strings
    for the same title number.
    """
    q = f"""
    WITH ranked AS (
      SELECT id,
        COALESCE(TRIM(book::text), '') AS bk,
        TRIM(title_num::text) AS tn,
        ROW_NUMBER() OVER (
          PARTITION BY COALESCE(TRIM(book::text), ''), title_num
          ORDER BY {_CODAL_ART_ORDER_SQL}
        ) AS rn
      FROM {table}
      WHERE title_num IS NOT NULL
    )
    SELECT bk, tn, id FROM ranked WHERE rn = 1
    """
    cur.execute(q)
    out: dict[str, str] = {}
    for bk, tn, id_val in cur.fetchall():
        out[f"{bk}|{tn}"] = str(id_val)
    return out


def _partition_chapter_first_by_context(cur, table: str) -> dict[str, str]:
    """
    First row id per (book, title_num, chapter_label) in codal order.
    Key: "{book}|{title_num}|{chapter_label_key}" — prevents duplicate chapter names
    like "General Provisions" appearing in multiple titles from sharing one boundary entry.
    """
    key_expr = _LABEL_KEY_SQL.format(col="chapter_label")
    q = f"""
    WITH ranked AS (
      SELECT id,
        COALESCE(TRIM(book::text), '') AS bk,
        COALESCE(TRIM(title_num::text), '') AS tn,
        {key_expr} AS lk,
        ROW_NUMBER() OVER (
          PARTITION BY
            COALESCE(TRIM(book::text), ''),
            COALESCE(TRIM(title_num::text), ''),
            {key_expr}
          ORDER BY {_CODAL_ART_ORDER_SQL}
        ) AS rn
      FROM {table}
      WHERE chapter_label IS NOT NULL AND TRIM(chapter_label) <> ''
    )
    SELECT bk, tn, lk, id FROM ranked WHERE rn = 1
    """
    cur.execute(q)
    out: dict[str, str] = {}
    for bk, tn, lk, id_val in cur.fetchall():
        out[f"{bk}|{tn}|{lk}"] = str(id_val)
    return out


def _partition_section_first_by_context(cur, table: str) -> dict[str, str]:
    """
    First row id per (book, title_num, chapter_label_key, section_label_key) in codal order.
    Key: "{book}|{title_num}|{chapter_label_key}|{section_label_key}" — prevents section
    names like "Section 1." from colliding across different chapters.
    """
    ch_key = _LABEL_KEY_SQL.format(col="chapter_label")
    sec_key = _LABEL_KEY_SQL.format(col="section_label")
    q = f"""
    WITH ranked AS (
      SELECT id,
        COALESCE(TRIM(book::text), '') AS bk,
        COALESCE(TRIM(title_num::text), '') AS tn,
        COALESCE({ch_key}, '') AS clk,
        {sec_key} AS slk,
        ROW_NUMBER() OVER (
          PARTITION BY
            COALESCE(TRIM(book::text), ''),
            COALESCE(TRIM(title_num::text), ''),
            COALESCE({ch_key}, ''),
            {sec_key}
          ORDER BY {_CODAL_ART_ORDER_SQL}
        ) AS rn
      FROM {table}
      WHERE section_label IS NOT NULL AND TRIM(section_label) <> ''
    )
    SELECT bk, tn, clk, slk, id FROM ranked WHERE rn = 1
    """
    cur.execute(q)
    out: dict[str, str] = {}
    for bk, tn, clk, slk, id_val in cur.fetchall():
        out[f"{bk}|{tn}|{clk}|{slk}"] = str(id_val)
    return out


def fetch_codal_family_bounds(cur, table_name: str) -> dict:
    """
    For rpc_codal / civ_codal / rcc_codal / labor_codal: structural "start" row ids in codal order.
    Keys:
      book_start          : {book -> id}
      title_label         : {normalized_label -> id}  (fallback)
      title_start_book_num: {"{book}|{title_num}" -> id}
      chapter_start       : {"{book}|{title_num}|{chapter_label_key}" -> id}
      section_start       : {"{book}|{title_num}|{chapter_label_key}|{section_label_key}" -> id}
      chapter_label       : {normalized_label -> id}  (legacy fallback, single-key)
      section_label       : {normalized_label -> id}  (legacy fallback, single-key)
    """
    if table_name not in ("rpc_codal", "civ_codal", "rcc_codal", "labor_codal"):
        raise ValueError(f"Unsupported table: {table_name}")

    bounds: dict = {
        "book_start": {},
        "title_label": {},
        "chapter_label": {},
        "section_label": {},
        "title_start_book_num": {},
        "chapter_start": {},
        "section_start": {},
    }

    try:
        bounds["title_label"] = _partition_first_label_ids(cur, table_name, "title_label")
    except Exception:
        pass
    try:
        bounds["chapter_label"] = _partition_first_label_ids(cur, table_name, "chapter_label")
    except Exception:
        pass
    try:
        bounds["section_label"] = _partition_first_label_ids(cur, table_name, "section_label")
    except Exception:
        pass
    try:
        bounds["book_start"] = _partition_first_book_ids(cur, table_name)
    except Exception:
        pass
    try:
        bounds["title_start_book_num"] = _partition_title_start_by_book_and_num(cur, table_name)
    except Exception:
        pass
    try:
        bounds["chapter_start"] = _partition_chapter_first_by_context(cur, table_name)
    except Exception:
        pass
    try:
        bounds["section_start"] = _partition_section_first_by_context(cur, table_name)
    except Exception:
        pass

    return bounds
