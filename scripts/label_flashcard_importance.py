#!/usr/bin/env python3
"""
Assign flashcard_concepts.importance_tier from Bar syllabus topics (JSON).

- core: TOS-like match score >= threshold, OR case_count >= min_case_count_force_core
- peripheral: everything else (hidden by default from GET /sc_decisions/flashcard_concepts)

Defaults (0.10 / 12) pair with API bar exam focus: labeled \"core\" rows with TOS score below
FLASHCARD_BAR_MIN_TOS_SCORE are omitted unless ?bar_focus=0.

Edit scripts/data/bar_tos_topics.json with official Table of Specifications text for best results.

Prerequisites:
  - sql/flashcard_concepts_importance_migration.sql applied
  - DB_CONNECTION_STRING (or api/local.settings.json Values)

Usage:
  python scripts/label_flashcard_importance.py --dry-run
  python scripts/label_flashcard_importance.py
  python scripts/label_flashcard_importance.py --threshold 0.1 --topics path/to/topics.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_API = os.path.join(_ROOT, "api")
_DEFAULT_TOPICS = os.path.join(_ROOT, "scripts", "data", "bar_tos_topics.json")

if _API not in sys.path:
    sys.path.insert(0, _API)


_STOP = frozenset(
    """
    the and for are but not you all can her was one our out day get has him his how its may new now old
    see two way who boy did let put say she too use that this with from they been into only such than then
    them well were also each made many some time very when which while your about after being both could
    first have here just like more most must over said same these those under upon what will would per via
    any may its their there than then them this shall such""".split()
)


def _load_db_url() -> str:
    env = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if env:
        return env
    settings_path = os.path.join(_API, "local.settings.json")
    if os.path.isfile(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        return (data.get("Values") or {}).get("DB_CONNECTION_STRING", "").strip()
    return ""


def tokenize(text: str) -> frozenset:
    if not text:
        return frozenset()
    words = re.findall(r"[a-záéíóúñ]{2,}", text.lower())
    return frozenset(w for w in words if w not in _STOP)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def load_topics(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    topics = data.get("topics")
    if not isinstance(topics, list) or not topics:
        raise SystemExit(f"No topics[] in {path}")
    out = []
    for t in topics:
        if not isinstance(t, dict) or not t.get("id"):
            continue
        out.append(
            {
                "id": str(t["id"]).strip(),
                "text": str(t.get("text") or ""),
                "keywords": t.get("keywords") if isinstance(t.get("keywords"), list) else [],
            }
        )
    if not out:
        raise SystemExit(f"No valid topics in {path}")
    return out


def best_topic_score(blob: str, topics: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
    toks = tokenize(blob)
    best_id: Optional[str] = None
    best = 0.0
    blob_l = blob.lower()
    for t in topics:
        tid = t["id"]
        ttoks = tokenize(t.get("text") or "")
        base = jaccard(toks, ttoks)
        bonus = 0.0
        for k in t.get("keywords") or []:
            kk = str(k).strip().lower()
            if len(kk) >= 2 and kk in blob_l:
                bonus = max(bonus, 0.14)
        score = min(1.0, base + bonus)
        if score > best:
            best = score
            best_id = tid
    return best_id, best


def classify_row(
    term: str,
    definition: str,
    case_count: int,
    topics: List[Dict[str, Any]],
    threshold: float,
    min_case_force: int,
) -> Tuple[str, Optional[str], float]:
    blob = f"{term}\n{definition}"
    bid, sc = best_topic_score(blob, topics)
    cc = int(case_count or 0)
    if cc >= min_case_force:
        return "core", bid, sc
    if sc >= threshold:
        return "core", bid, sc
    return "peripheral", bid, sc


def main() -> None:
    parser = argparse.ArgumentParser(description="Label flashcard importance_tier from TOS JSON")
    parser.add_argument(
        "--topics",
        default=_DEFAULT_TOPICS,
        help=f"Path to topics JSON (default: {_DEFAULT_TOPICS})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.10,
        help="Min best TOS score for core (default 0.10). Raise to cull harder.",
    )
    parser.add_argument(
        "--min-case-count-force-core",
        type=int,
        default=12,
        help="Concepts with this many source cases or more stay core regardless of TOS score (default 12).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print stats only; do not UPDATE")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per executemany batch")
    args = parser.parse_args()

    conn_str = _load_db_url()
    if not conn_str:
        print("DB_CONNECTION_STRING not set and api/local.settings.json missing Values.DB_CONNECTION_STRING.")
        sys.exit(1)
    if ":6432/" in conn_str:
        conn_str = conn_str.replace(":6432/", ":5432/")

    topics = load_topics(args.topics)
    print(f"Loaded {len(topics)} topics from {args.topics}")

    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(conn_str, connect_timeout=120)
    conn.autocommit = False
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT term_key, term, definition, case_count
            FROM flashcard_concepts
            """
        )
        rows = cur.fetchall() or []
        cur.close()
    except Exception as e:
        conn.close()
        print(f"Failed to read flashcard_concepts: {e}")
        print("Apply sql/flashcard_concepts_importance_migration.sql first.")
        sys.exit(1)

    if not rows:
        print("No rows in flashcard_concepts.")
        conn.close()
        return

    updates: List[Tuple[Any, ...]] = []
    n_core = n_periph = 0
    for r in rows:
        tier, bid, sc = classify_row(
            r.get("term") or "",
            (r.get("definition") or "").strip(),
            int(r.get("case_count") or 0),
            topics,
            args.threshold,
            args.min_case_count_force_core,
        )
        if tier == "core":
            n_core += 1
        else:
            n_periph += 1
        updates.append((tier, bid, sc, r.get("term_key")))

    print(f"Would label: core={n_core}, peripheral={n_periph} (total {len(rows)})")
    print(f"threshold={args.threshold}, min_case_count_force_core={args.min_case_count_force_core}")

    if args.dry_run:
        sample = [u for u in updates if u[0] == "peripheral"][:8]
        if sample:
            print("Sample peripheral term_keys:", [s[3] for s in sample])
        conn.close()
        return

    cur = conn.cursor()
    from psycopg2.extras import execute_values

    upd_sql = """
        UPDATE flashcard_concepts AS fc
        SET importance_tier = v.tier,
            tos_topic_id = v.tid,
            tos_match_score = v.sc
        FROM (VALUES %s) AS v(tier, tid, sc, tkey)
        WHERE fc.term_key = v.tkey
    """
    batch = args.batch_size
    for i in range(0, len(updates), batch):
        chunk = updates[i : i + batch]
        vals = [(c[0], c[1], c[2], c[3]) for c in chunk]
        execute_values(
            cur,
            upd_sql,
            vals,
            template="(%s::text, %s::text, %s::double precision, %s::text)",
            page_size=len(vals),
        )

    conn.commit()
    cur.close()
    print(f"Updated {len(updates)} rows.")

    try:
        from cache import cache_delete
        from config import FLASHCARD_CONCEPTS_CACHE_KEY

        if cache_delete(FLASHCARD_CONCEPTS_CACHE_KEY):
            print(f"Invalidated Redis key {FLASHCARD_CONCEPTS_CACHE_KEY!r}.")
    except Exception as inv_ex:
        print(f"[note] Redis cache invalidation skipped: {inv_ex}")

    conn.close()


if __name__ == "__main__":
    main()
