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


_CANONICAL_BAR = frozenset(
    {
        "Civil Law",
        "Commercial Law",
        "Criminal Law",
        "Labor Law",
        "Legal Ethics",
        "Political Law",
        "Remedial Law",
        "Taxation Law",
    }
)


def normalize_bar_subject_label(raw: Any) -> str:
    """Map free-text digest / Bar labels to one canonical subject (aligned with frontend subjectNormalize)."""
    if raw is None:
        return ""
    t = str(raw).strip()
    if t in _CANONICAL_BAR:
        return t
    s = t.lower()
    if "civil service" in s or "civil-service" in s or re.search(r"\bcsc\b", s):
        return "Labor Law"
    # Word-boundary style: avoid "penalties"→penal, "belabor"→labor (aligned with frontend subjectNormalize).
    if re.search(r"\bcommercial\b", s) or re.search(r"\bmercantile\b", s):
        return "Commercial Law"
    if re.search(r"\bcriminal\b", s) or re.search(r"\bpenal\b", s):
        return "Criminal Law"
    if re.search(r"\blabor\b", s) or "social legislat" in s:
        return "Labor Law"
    if re.search(r"\bethics\b", s) or "judicial ethics" in s:
        return "Legal Ethics"
    if re.search(r"\bpolitical\b", s) or re.search(r"\bconstitutional\b", s):
        return "Political Law"
    if re.search(r"\bremedial\b", s) or re.search(r"\bprocedure\b", s) or re.search(r"\brules of court\b", s):
        return "Remedial Law"
    if "practical exercise" in s:
        return "Remedial Law"
    if "land title" in s:
        return "Civil Law"
    if "taxation" in s or re.search(r"\btax\b", s):
        return "Taxation Law"
    if re.search(r"\bcivil\b", s):
        return "Civil Law"
    return t


def _segment_after_primary_from_text(blob: str) -> str:
    """If *blob* contains ``Primary:``, return only that segment (strip ``Secondary:`` and trailing clauses)."""
    b = (blob or "").strip()
    if not b:
        return ""
    m = re.search(r"primary\s*:\s*", b, flags=re.IGNORECASE)
    if not m:
        return b
    rest = b[m.end() :].strip()
    sec = re.search(r"\bsecondary\s*:", rest, flags=re.IGNORECASE)
    if sec:
        rest = rest[: sec.start()].strip()
    if ";" in rest:
        rest = rest.split(";")[0].strip()
    return rest


def extract_digest_primary_from_item(item: Mapping[str, Any], case_subject: str) -> str:
    """Primary Bar subject from a legal_concepts JSON item; ignores Secondary. Fallback: case row subject."""
    if not isinstance(item, dict):
        return normalize_bar_subject_label(case_subject)
    ps = item.get("primary_subject")
    if isinstance(ps, str) and ps.strip():
        return normalize_bar_subject_label(ps.strip())
    blob_parts: List[str] = []
    for key in ("subject", "subjects", "topic", "bar_subject"):
        v = item.get(key)
        if isinstance(v, str) and v.strip():
            blob_parts.append(v.strip())
        elif isinstance(v, list) and v:
            blob_parts.extend(str(x).strip() for x in v[:5] if str(x).strip())
    blob = " ".join(blob_parts).strip()
    if blob and re.search(r"primary\s*:", blob, re.IGNORECASE):
        seg = _segment_after_primary_from_text(blob)
        if seg:
            return normalize_bar_subject_label(seg)
    if blob:
        return normalize_bar_subject_label(blob)
    return normalize_bar_subject_label(case_subject)


def get_primary_subject(sources: Any) -> str:
    """Modal canonical subject from each source's ``digest_primary`` (digest Primary only).

    Legacy rows without ``digest_primary`` fall back to modal of normalized ``subject``.
    """
    if not isinstance(sources, list) or not sources:
        return ""
    dp_freq: Dict[str, int] = {}
    leg_freq: Dict[str, int] = {}
    for src in sources:
        if not isinstance(src, dict):
            continue
        dp = (src.get("digest_primary") or "").strip()
        if dp:
            lab = normalize_bar_subject_label(dp)
            if lab:
                dp_freq[lab] = dp_freq.get(lab, 0) + 1
            continue
        s = (src.get("subject") or "").strip()
        if s:
            lab = normalize_bar_subject_label(s)
            if lab:
                leg_freq[lab] = leg_freq.get(lab, 0) + 1
    if dp_freq:
        return max(dp_freq, key=lambda k: dp_freq[k])
    if leg_freq:
        return max(leg_freq, key=lambda k: leg_freq[k])
    return ""


def merge_concept_into_map(
    concepts_map: MutableMapping[str, Any],
    term: str,
    definition: str,
    case_id: Any,
    case_number: str,
    title: str,
    date_str: str,
    digest_primary: str,
    case_subject: str,
) -> None:
    if not term or not str(term).strip():
        return
    term = str(term).strip()
    definition = (definition or "").strip()
    key = re.sub(r"\s+", " ", term).lower()
    dp_norm = normalize_bar_subject_label(digest_primary)
    src = {
        "case_id": case_id,
        "case_number": case_number or "",
        "title": title or "",
        "date_str": date_str or "",
        "subject": case_subject or "",
        "digest_primary": dp_norm or "",
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
            d_primary = extract_digest_primary_from_item(item, subj)
            merge_concept_into_map(
                concepts_map, t, d, case_id, case_number, title, date_str, d_primary, subj
            )

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
