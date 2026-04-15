"""
Read-only audit: compare present-view *_codal rows with active article_versions
for the same legal_codes row. Surfaces coverage gaps and content hash mismatches.

Purpose: evidence for whether article_versions stays in sync with codal tables
when amendments are applied only to *_codal (or vice versa).

Inputs:
  - DB_CONNECTION_STRING env var, OR
  - api/local.settings.json Values.DB_CONNECTION_STRING

Usage (from repo root):
  python scripts/audit_codal_article_versions.py
  python scripts/audit_codal_article_versions.py --spot 125,134,134-A,135,136
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

_REPO_ROOT = Path(__file__).resolve().parents[1]

_col_cache: dict[str, list[str]] = {}


def _table_columns(cur, table: str) -> list[str]:
    if table not in _col_cache:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table,),
        )
        _col_cache[table] = [r["column_name"] for r in cur.fetchall()]
    return _col_cache[table]


def _codal_body_expr(cur, table: str) -> str:
    cols = set(_table_columns(cur, table))
    parts = []
    if "content_md" in cols:
        parts.append("NULLIF(TRIM(BOTH FROM content_md::text), '')")
    if "content" in cols:
        parts.append("NULLIF(TRIM(BOTH FROM content::text), '')")
    if not parts:
        return "''::text"
    return "COALESCE(" + ", ".join(parts) + ", '')::text"


def get_db_connection():
    conn_str = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if not conn_str:
        p = _REPO_ROOT / "api" / "local.settings.json"
        if p.is_file():
            with open(p, encoding="utf-8") as f:
                conn_str = json.load(f).get("Values", {}).get("DB_CONNECTION_STRING", "").strip()
    if not conn_str:
        print("Missing DB_CONNECTION_STRING (env or api/local.settings.json).", file=sys.stderr)
        sys.exit(2)
    return psycopg2.connect(conn_str)


def _norm_key(s) -> str:
    if s is None:
        return ""
    return str(s).strip()


def _body_hash(text: str | None) -> str:
    raw = (text or "").replace("\r\n", "\n").strip()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# article_versions often stores LexCode-style lead-in; *_codal stores body MD only.
_ARTICLE_LEAD = re.compile(
    r"^Article\s+[\w.-]+(?:\s+\*\*[^*]+\*\*)?\s*-\s*",
    re.IGNORECASE,
)


def _strip_av_article_lead(s: str | None) -> str:
    t = (s or "").replace("\r\n", "\n").strip()
    return _ARTICLE_LEAD.sub("", t, count=1).strip()


def _codal_join_key(short: str, art_col_val) -> str:
    """Match LexCode / codex provision keys where *_codal uses a different id than article_versions."""
    raw = _norm_key(art_col_val)
    if short == "FC" and "-" in raw:
        return _norm_key(raw.split("-")[-1])
    return raw


# LexCode / codex special codals: (short_name, table, article_column)
SPECIAL_CODALS: list[tuple[str, str, str]] = [
    ("RPC", "rpc_codal", "article_num"),
    ("CIV", "civ_codal", "article_num"),
    ("RCC", "rcc_codal", "article_num"),
    ("LABOR", "labor_codal", "article_num"),
    ("FC", "fc_codal", "article_num"),
    ("ROC", "roc_codal", "rule_section_label"),
    ("CONST", "consti_codal", "article_num"),
]


def _codal_where_sql(cur, short: str, table: str) -> tuple[str, tuple]:
    """Match codex.py filtering when possible; otherwise scan the whole table."""
    cols = set(_table_columns(cur, table))
    if "book_code" in cols:
        return "book_code = %s", (short.upper(),)
    if table == "rpc_codal":
        return "book IS NOT NULL", ()
    return "TRUE", ()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--spot",
        type=str,
        default="",
        help="Comma-separated article keys to print detail for (e.g. 125,136)",
    )
    args = ap.parse_args()
    spot_set = {_norm_key(x) for x in args.spot.split(",") if _norm_key(x)}

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT code_id, short_name FROM legal_codes ORDER BY short_name")
    code_by_short = {r["short_name"].upper(): r["code_id"] for r in cur.fetchall()}

    print("=== codal vs article_versions (active: valid_to IS NULL) ===\n")

    for short, table, art_col in SPECIAL_CODALS:
        code_id = code_by_short.get(short)
        if not code_id:
            print(f"[{short}] SKIP: no legal_codes row\n")
            continue

        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = %s
            ) AS ok
            """,
            (table,),
        )
        if not cur.fetchone()["ok"]:
            print(f"[{short}] SKIP: table {table} missing\n")
            continue

        where_sql, where_params = _codal_where_sql(cur, short, table)
        cur.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM {table}
            WHERE {where_sql}
            """,
            where_params,
        )
        codal_n = cur.fetchone()["n"]

        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM article_versions
            WHERE code_id = %s AND valid_to IS NULL
            """,
            (code_id,),
        )
        av_n = cur.fetchone()["n"]

        body_sql = _codal_body_expr(cur, table)
        cur.execute(
            f"""
            SELECT
              TRIM(BOTH FROM {art_col}::text) AS art_key,
              {body_sql} AS body
            FROM {table}
            WHERE {where_sql}
            """,
            where_params,
        )
        codal_rows = cur.fetchall()
        codal_by_key = {_codal_join_key(short, r["art_key"]): r["body"] for r in codal_rows}

        cur.execute(
            """
            SELECT TRIM(BOTH FROM article_number::text) AS art_key, content
            FROM article_versions
            WHERE code_id = %s AND valid_to IS NULL
            """,
            (code_id,),
        )
        av_rows = cur.fetchall()
        av_by_key = {_norm_key(r["art_key"]): r["content"] for r in av_rows}

        keys_codal = set(codal_by_key)
        keys_av = set(av_by_key)
        both = keys_codal & keys_av
        only_codal = keys_codal - keys_av
        only_av = keys_av - keys_codal

        mismatches_raw = 0
        mismatches_norm = 0
        codes_with_article_lead = {"RPC", "CIV", "RCC", "LABOR", "FC"}
        for k in sorted(both):
            cb = codal_by_key[k]
            ab = av_by_key[k]
            if _body_hash(cb) != _body_hash(ab):
                mismatches_raw += 1
            av_cmp = _strip_av_article_lead(ab) if short in codes_with_article_lead else ab
            if _body_hash(cb) != _body_hash(av_cmp):
                mismatches_norm += 1

        print(f"[{short}] code_id={code_id} table={table}")
        print(f"  codal rows: {codal_n} | active article_versions: {av_n}")
        line = (
            f"  keys: in_both={len(both)} only_codal={len(only_codal)} only_av={len(only_av)} "
            f"content_mismatch_raw={mismatches_raw}"
        )
        if short in codes_with_article_lead:
            line += f" mismatch_after_strip_article_lead={mismatches_norm}"
        if short == "RPC" and mismatches_norm > 0:
            line += (
                "  (note: strip only removes 'Article N. **title** -'; "
                "RPC AV often keeps a plain-title sentence codal omits; counts as mismatch.)"
            )
        print(line)

        if only_codal and len(only_codal) <= 15:
            print(f"  only_codal sample: {sorted(only_codal, key=str)[:15]}")
        elif only_codal:
            sample = sorted(only_codal, key=str)[:8]
            print(f"  only_codal (first 8 of {len(only_codal)}): {sample}")

        if only_av and len(only_av) <= 15:
            print(f"  only_av sample: {sorted(only_av, key=str)[:15]}")
        elif only_av:
            sample = sorted(only_av, key=str)[:8]
            print(f"  only_av (first 8 of {len(only_av)}): {sample}")

        if short == "RPC" and art_col == "article_num":
            cur.execute(
                """
                SELECT article_num::text AS k, COUNT(*) AS c
                FROM rpc_codal
                WHERE book IS NOT NULL
                GROUP BY article_num
                HAVING COUNT(*) > 1
                ORDER BY c DESC
                LIMIT 10
                """
            )
            dupes = cur.fetchall()
            if dupes:
                print(f"  rpc_codal duplicate article_num (book split): {dupes}")

        # Spot rows
        for sk in sorted(spot_set & (keys_codal | keys_av)):
            if sk not in keys_codal and sk not in keys_av:
                continue
            in_c = sk in codal_by_key
            in_a = sk in av_by_key
            cb = codal_by_key.get(sk) if in_c else None
            ab = av_by_key.get(sk) if in_a else None
            hc = _body_hash(cb) if in_c else None
            ha = _body_hash(ab) if in_a else None
            avn = _strip_av_article_lead(ab) if in_a and short in codes_with_article_lead else ab
            hn = _body_hash(avn) if in_a else None
            lc = len(cb or "") if in_c else 0
            la = len(ab or "") if in_a else 0
            print(
                f"  spot[{sk}] codal={in_c} av={in_a} len_codal={lc} len_av={la} "
                f"md5_raw_match={hc == ha if in_c and in_a else 'n/a'}"
                + (
                    f" md5_norm_match={hc == hn if in_c and in_a else 'n/a'}"
                    if short in codes_with_article_lead
                    else ""
                )
            )

        print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
