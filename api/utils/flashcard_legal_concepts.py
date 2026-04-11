"""
Shared logic for digest legal_concepts → deduplicated flashcard concept list.
Used by the flashcard_concepts API and the populate script.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple


def parse_legal_concepts(raw: Any) -> List[Dict[str, Any]]:
    """Normalize legal_concepts from DB (json/jsonb/text/list) into list of dicts with term/definition."""
    if raw is None:
        return []
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except Exception:
            return []
    if isinstance(raw, dict):
        if raw.get("term") or raw.get("concept") or raw.get("title") or raw.get("name"):
            return [raw]
        for key in ("legal_concepts", "concepts", "items", "data"):
            inner = raw.get(key)
            if isinstance(inner, list):
                return parse_legal_concepts(inner)
            if isinstance(inner, dict):
                return parse_legal_concepts(inner)
        return []
    if isinstance(raw, list):
        out: List[Dict[str, Any]] = []
        for x in raw:
            if isinstance(x, dict):
                out.append(x)
            elif isinstance(x, str) and x.strip():
                out.append({"term": x.strip(), "definition": ""})
        return out
    if isinstance(raw, str):
        try:
            if not raw.strip():
                return []
            parsed = json.loads(raw)
            return parse_legal_concepts(parsed)
        except Exception:
            return []
    return []


def concept_term(item: Mapping[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    return (
        item.get("term")
        or item.get("concept")
        or item.get("title")
        or item.get("name")
        or item.get("label")
        or item.get("key")
        or ""
    ).strip()


def concept_definition(item: Mapping[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    return (
        item.get("definition")
        or item.get("content")
        or item.get("text")
        or item.get("summary")
        or ""
    ).strip()


def _source_latest_sort_key(src: Mapping[str, Any]) -> Tuple[str, int]:
    """Prefer latest decision date, then highest case_id (tiebreak)."""
    ds = str(src.get("date_str") or "").strip()
    if len(ds) < 10:
        ds = "0000-00-00"
    cid = src.get("case_id")
    try:
        cid_num = int(cid) if cid is not None else 0
    except (TypeError, ValueError):
        cid_num = 0
    return (ds, cid_num)


def sources_keep_latest_only(sources: Any) -> List[Dict[str, Any]]:
    """Flashcards cite only the most recent SC case that mentioned the concept."""
    if not isinstance(sources, list) or not sources:
        return []
    valid = [s for s in sources if isinstance(s, dict)]
    if not valid:
        return []
    best = max(valid, key=_source_latest_sort_key)
    return [best]


def get_primary_subject(sources: Any) -> str:
    """Return the most frequent (modal) subject across all sources.

    This must be called BEFORE sources_keep_latest_only so the full set of
    source cases is available.  Falls back to the single remaining source's
    subject if called post-collapse.
    """
    if not isinstance(sources, list) or not sources:
        return ""
    freq: Dict[str, int] = {}
    for src in sources:
        if not isinstance(src, dict):
            continue
        s = (src.get("subject") or "").strip()
        if s:
            freq[s] = freq.get(s, 0) + 1
    if not freq:
        return ""
    return max(freq, key=lambda k: freq[k])


def merge_concept_into_map(
    concepts_map: MutableMapping[str, Any],
    term: str,
    definition: str,
    case_id: Any,
    case_number: str,
    title: str,
    date_str: str,
    subj: str,
) -> None:
    if not term or not str(term).strip():
        return
    term = str(term).strip()
    definition = (definition or "").strip()
    key = re.sub(r"\s+", " ", term).lower()
    src = {
        "case_id": case_id,
        "case_number": case_number or "",
        "title": title or "",
        "date_str": date_str or "",
        "subject": subj or "",
    }
    if key not in concepts_map:
        concepts_map[key] = {
            "term": term,
            "definition": definition,
            "sources": [],
            "_seen_case_ids": set(),
        }
    else:
        if definition and len(definition) > len(concepts_map[key].get("definition") or ""):
            concepts_map[key]["definition"] = definition
    ent = concepts_map[key]
    if case_id not in ent["_seen_case_ids"]:
        ent["_seen_case_ids"].add(case_id)
        ent["sources"].append(src)


def merge_digest_rows_to_concepts_list(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Build the same deduplicated list as the legacy flashcard_concepts endpoint from sc_decided_cases rows."""
    concepts_map: Dict[str, Any] = {}
    for row in rows or []:
        case_id = row.get("id")
        case_number = row.get("case_number") or ""
        title = row.get("short_title") or row.get("title") or ""
        date_str = row.get("date_str") or ""
        subj = row.get("subject") or ""

        for item in parse_legal_concepts(row.get("legal_concepts")):
            if not isinstance(item, dict):
                continue
            t = concept_term(item)
            if not t:
                continue
            d = concept_definition(item)
            merge_concept_into_map(concepts_map, t, d, case_id, case_number, title, date_str, subj)

    out: List[Dict[str, Any]] = []
    for _k, ent in concepts_map.items():
        ent.pop("_seen_case_ids", None)
        all_sources = ent.get("sources") or []
        case_count = len(all_sources)
        out.append(
            {
                "term": ent["term"],
                "definition": ent.get("definition") or "",
                "sources": sources_keep_latest_only(all_sources),
                "primary_subject": get_primary_subject(all_sources),
                "case_count": case_count,
            }
        )
    return out


def term_key_for_term(term: str) -> str:
    return re.sub(r"\s+", " ", str(term).strip()).lower()


# Which case digests feed flashcards (populate script + API fallback must stay in sync).
FLASHCARD_SOURCE_YEAR_MIN = 1987
FLASHCARD_SOURCE_YEAR_MAX = 2025
FLASHCARD_SOURCE_DIVISION_PATTERN = "%en banc%"


def flashcard_digest_select_sql_and_params() -> Tuple[str, Tuple[Any, ...]]:
    """Rows from sc_decided_cases used to build merged legal-concept flashcards."""
    sql = """
            SELECT id, case_number, short_title, subject,
                   TO_CHAR(date, 'YYYY-MM-DD') AS date_str,
                   legal_concepts
            FROM sc_decided_cases
            WHERE legal_concepts IS NOT NULL
              AND length(trim(both from legal_concepts::text)) > 2
              AND trim(both from legal_concepts::text) NOT IN ('null', '{}', '[]')
              AND EXTRACT(YEAR FROM date) BETWEEN %s AND %s
              AND division IS NOT NULL
              AND division ILIKE %s
            """
    return (
        sql,
        (FLASHCARD_SOURCE_YEAR_MIN, FLASHCARD_SOURCE_YEAR_MAX, FLASHCARD_SOURCE_DIVISION_PATTERN),
    )
