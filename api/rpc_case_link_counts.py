"""Shared RPC jurisprudence link counts for LexCode (rpc/* and codex/versions)."""

from __future__ import annotations

import logging
import re
from typing import Any

# Mirror codex jurisprudence alias map (codex.py STATUTE_MAPPING + RPC mapping).
_RPC_LINK_COUNT_ALIASES = {
    "266-A": frozenset({"266-A", "335"}),
    "266-B": frozenset({"266-B", "335"}),
    "335": frozenset({"335", "266-A", "266-B"}),
}


def norm_rpc_provision_id(pid: Any) -> str:
    if pid is None:
        return ""
    s = str(pid).strip()
    s = re.sub(r"(?i)^article\s+", "", s)
    s = re.sub(r"(?i)^art\.\s*", "", s)
    return s.strip().rstrip(".").upper()


def rpc_article_lookup_keys(anum_raw: Any) -> frozenset[str]:
    a = norm_rpc_provision_id(anum_raw)
    if not a:
        return frozenset()
    keys = {a}
    aliases = _RPC_LINK_COUNT_ALIASES.get(a)
    if aliases:
        keys |= set(aliases)
    return frozenset(keys)


def rpc_statute_sql_predicate(alias: str = "statute_id") -> str:
    """Match LexCode RPC links whether statute_id is the short code or legal_codes.code_id (UUID)."""
    col = alias
    return f"""(
      UPPER(TRIM({col}::text)) = 'RPC'
      OR {col}::text = (
          SELECT code_id::text FROM legal_codes
          WHERE UPPER(TRIM(short_name)) = 'RPC' LIMIT 1
      )
    )"""


def load_rpc_paragraph_link_norm_map(cur) -> dict[str, dict[str, int]]:
    cur.execute(
        f"""
        SELECT provision_id,
               COALESCE(target_paragraph_index, -1) AS target_paragraph_index,
               COUNT(*) AS link_count
        FROM codal_case_links
        WHERE {rpc_statute_sql_predicate('statute_id')}
        GROUP BY provision_id, COALESCE(target_paragraph_index, -1)
        """
    )
    rows = cur.fetchall()
    norm_map: dict[str, dict[str, int]] = {}
    for r in rows:
        norm_art = norm_rpc_provision_id(r["provision_id"])
        if not norm_art:
            continue
        idx = r["target_paragraph_index"]
        try:
            idx_key = str(int(idx))
        except (TypeError, ValueError):
            idx_key = "-1"
        count = int(r["link_count"] or 0)
        if norm_art not in norm_map:
            norm_map[norm_art] = {}
        norm_map[norm_art][idx_key] = norm_map[norm_art].get(idx_key, 0) + count
    return norm_map


def apply_rpc_paragraph_links(articles: list, norm_map: dict[str, dict[str, int]]) -> None:
    for art in articles:
        anum = art.get("article_num") or art.get("article_number") or art.get("key_id")
        merged: dict[str, int] = {}
        for lk in rpc_article_lookup_keys(anum):
            bucket = norm_map.get(lk)
            if not bucket:
                continue
            for idx_key, cnt in bucket.items():
                merged[idx_key] = merged.get(idx_key, 0) + cnt
        art["paragraph_links"] = merged


def attach_rpc_link_counts(cur, articles: list) -> None:
    if not articles:
        return
    try:
        norm_map = load_rpc_paragraph_link_norm_map(cur)
        apply_rpc_paragraph_links(articles, norm_map)
    except Exception as e:
        logging.error("attach_rpc_link_counts: %s", e)
        for art in articles:
            art["paragraph_links"] = {}
