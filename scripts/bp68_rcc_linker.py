"""
bp68_rcc_linker.py
==================
2-Pass RAG Linker: pre-2019 Corporation Code (BP 68) cases → RCC provisions.

Links SC cases decided before 2019 (under Batas Pambansa Blg. 68) to their
equivalent provisions in the Revised Corporation Code (RA 11232, 2019).

How it works:
  PASS 1 (Router): AI reads the case digest and returns the RCC section(s) that
                   correspond to the BP 68 doctrine applied in the case.
  DB Fetch:        Fetches full text of candidate RCC sections.
  PASS 2 (Granular): AI confirms the link and identifies the exact paragraph index.

Committed links are tagged with decided_under='BP_68' so they can be
distinguished from post-2019 RCC links in the database.

Usage:
  python bp68_rcc_linker.py --limit 10              # dry-run, 10 cases
  python bp68_rcc_linker.py --limit 100 --commit    # write first 100
  python bp68_rcc_linker.py --commit --workers 5    # full run, 5 workers
  python bp68_rcc_linker.py --start_year 1980 --end_year 2000 --commit
"""

import os
import re
import sys
import json
import time
from typing import Optional
import argparse
import threading
import psycopg2


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            pass


_configure_stdio_utf8()
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai

from linker_genai_client import (
    get_linker_genai_client,
    get_linker_model_name,
    merge_local_settings_into_env,
)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
merge_local_settings_into_env()
DB_URL = (
    os.environ.get("DB_CONNECTION_STRING")
    or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
)
MODEL_NAME = get_linker_model_name()
client = None
db_pool: ThreadedConnectionPool = None  # type: ignore

# Only RCC for this linker
CODE_CONFIGS: dict = {
    "RCC": {
        "table": "rcc_codal",
        "name": "Revised Corporation Code of the Philippines",
        "subject_area": "Corporate Law",
    }
}

# ---------------------------------------------------------------------------
# BP 68 → RCC provision maps (used to guide the AI and for validation)
# ---------------------------------------------------------------------------

# 8 provisions where BP 68 section number shifted due to the new OPC chapter
# (RCC Sec 14 inserted new OPC definitions, pushing old Sec 14+ up by 1;
#  Sec 94 of BP68 renumbered to Sec 93 in RCC due to merged Sec 8/9).
BP68_SECTION_MAP: dict[str, str] = {
    # BP 68 sec → RCC sec
    "14": "15",
    "15": "16",
    "16": "17",
    "17": "18",
    "18": "19",
    "19": "20",
    "20": "21",
    "94": "93",
}

# Key doctrines developed under BP 68 and their primary RCC section(s)
BP68_DOCTRINE_MAP: dict[str, list[str]] = {
    "piercing the corporate veil": ["2", "30"],
    "business judgment rule": ["22", "30"],
    "corporate opportunity doctrine": ["33"],
    "trust fund doctrine": ["60", "61", "62", "63", "64", "65", "66"],
    "derivative suit": ["180", "30"],
    "interlocking directors": ["31", "32"],
    "ultra vires acts": ["44"],
    "merger successor liability": ["79"],
}

# Human-readable doctrine hints for the Pass 1 prompt
_DOCTRINE_HINT_LINES = "\n".join(
    f"  - {doc}: see RCC Sec {', '.join(secs)}"
    for doc, secs in BP68_DOCTRINE_MAP.items()
)

# Shift hint for the Pass 1 prompt
_SHIFT_HINT = (
    "Note: BP 68 sections 14-20 were renumbered to RCC sections 15-21 "
    "(RCC inserted a new Sec 14 for OPC definitions). BP 68 Sec 94 = RCC Sec 93."
)

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    global db_pool
    if db_pool is None:
        # keepalives prevent Azure PostgreSQL from dropping long-idle connections
        db_pool = ThreadedConnectionPool(
            1, 50, dsn=DB_URL,
            keepalives=1, keepalives_idle=60, keepalives_interval=10, keepalives_count=5,
        )
    conn = db_pool.getconn()
    # Validate the connection is still alive; replace if not
    try:
        conn.cursor().execute("SELECT 1")
    except Exception:
        db_pool.putconn(conn, close=True)
        conn = db_pool.getconn()
    return conn


def release(conn):
    if db_pool:
        db_pool.putconn(conn)


def _mark_processed(case_id: int) -> None:
    """Record that this case has been evaluated (even if 0 links found)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bp68_processed_cases (case_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (case_id,),
        )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
    finally:
        release(conn)


# ---------------------------------------------------------------------------
# Pre-load RCC section index
# ---------------------------------------------------------------------------

def load_article_index() -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    index: dict = {"RCC": {}}

    cur.execute("SELECT article_num, content_md FROM rcc_codal")
    for row in cur.fetchall():
        raw_num = str(row[0])
        clean_num = re.sub(
            r"^(Article|Section|Art\.)\s+", "", raw_num, flags=re.IGNORECASE
        ).strip()
        text = str(row[1] or "")
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        index["RCC"][clean_num] = {
            "content": text,
            "paragraph_count": len(paragraphs),
        }

    cur.close()
    release(conn)
    return index


def _canonical_provision_key(article_index: dict, art_clean: str) -> Optional[str]:
    bucket = article_index.get("RCC") or {}
    return art_clean if art_clean in bucket else None


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _genai_generate_with_retry(prompt: str, max_retries: int = 5) -> str:
    delay = 10
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=genai.types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return response.text
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            if is_rate_limit and attempt < max_retries - 1:
                print(f"    [RATE] 429 — waiting {delay}s before retry {attempt + 2}/{max_retries}...", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            raise


# ---------------------------------------------------------------------------
# PASS 1 — Router: which RCC section(s) does this pre-2019 case touch?
# ---------------------------------------------------------------------------

PASS1_SCHEMA = """
{
  "hits": [
    {"code_id": "RCC", "article": "23"},
    {"code_id": "RCC", "article": "30"}
  ]
}
"""


def pass1_route(case: dict) -> list:
    prompt = f"""
You are a Philippine corporate law expert. The case below was decided under
Batas Pambansa Blg. 68 (the 1980 Corporation Code). Your task is to identify
which section(s) of the Revised Corporation Code (RA 11232, 2019) correspond
to the legal provision(s) the case INTERPRETS or APPLIES.

The RCC largely re-enacted BP 68 with renumbering and amendments. Map the
BP 68 provision to the RCC equivalent section.

DOCTRINE-TO-RCC MAPPING HINTS:
{_DOCTRINE_HINT_LINES}

RENUMBERING NOTE:
{_SHIFT_HINT}

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or 'N/A'}
Issues: {case.get('digest_issues') or 'N/A'}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}
Ruling: {case.get('digest_ruling') or ''}
Significance: {case.get('digest_significance') or ''}

TASK:
Your PRIMARY basis for identifying the correct RCC section are the **Issues**
and **Ratio Decidendi**. The Facts and Doctrine provide context.

RULES:
- Output ONLY RCC section numbers (bare integers, e.g. "23", "30").
- The JSON key is "article" but the value is the RCC **section** number.
- If the case does not interpret any BP 68 provision that has an RCC equivalent,
  return {{"hits": []}}
- Limit to sections truly interpreted/applied, not just cited in passing.

OUTPUT (JSON only):
{PASS1_SCHEMA}
"""
    try:
        time.sleep(0.5)
        text = _genai_generate_with_retry(prompt)
        data = json.loads(text)
        return data.get("hits", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"    [WARN] PASS-1 error: {exc}", flush=True)
        return []


# ---------------------------------------------------------------------------
# PASS 2 — Granular: exact paragraph index
# ---------------------------------------------------------------------------

PASS2_SCHEMA = """
{
  "links": [
    {
      "code_id": "RCC",
      "article": "23",
      "paragraph_index": -1,
      "summary": "..."
    }
  ]
}
"""


def pass2_granular(case: dict, candidates: list, article_index: dict) -> list:
    if not candidates:
        return []

    article_blocks = []
    for code_id, art_num in candidates:
        entry = article_index["RCC"].get(art_num)
        if not entry:
            continue
        article_blocks.append(
            f"[RCC] Section {art_num}:\n{entry['content'][:800]}"
        )

    if not article_blocks:
        return []

    articles_section = "\n\n---\n\n".join(article_blocks)

    prompt = f"""
You are a Philippine corporate law expert finalising a jurisprudence database.

The case below was decided under BP 68 (1980 Corporation Code) but is being
linked to the equivalent Revised Corporation Code (RCC) provision.

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or ''}
Issues: {case.get('digest_issues') or ''}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}
Ruling: {case.get('digest_ruling') or ''}

CANDIDATE RCC PROVISIONS:
{articles_section}

For EACH candidate provision above:
1. Confirm whether the case truly interprets/applies the equivalent BP 68
   provision (include it only if yes).
2. Identify the exact 0-based paragraph index that the ruling focuses on,
   or -1 if the ruling is about the provision in general.
   Count paragraph breaks (blank lines) starting from 0.
3. Write a concise one-to-two sentence summary of the holding regarding that
   provision, noting that it was decided under the old Corporation Code.

RULES:
- "article" must be the bare RCC section number (e.g. "23"), no prefix.
- "paragraph_index" must be an integer (-1 for general).

OUTPUT (JSON only):
{PASS2_SCHEMA}
"""
    try:
        time.sleep(0.5)
        text = _genai_generate_with_retry(prompt)
        data = json.loads(text)
        return data.get("links", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"    [WARN] PASS-2 error: {exc}", flush=True)
        return []


# ---------------------------------------------------------------------------
# Main per-case worker
# ---------------------------------------------------------------------------

def process_case(case: dict, article_index: dict, dry_run: bool) -> int:
    title = case.get("short_title", str(case["id"]))[:50]

    # PASS 1
    raw_hits = pass1_route(case)
    if not raw_hits:
        _mark_processed(case["id"])
        return 0

    valid_candidates = []
    for hit in raw_hits:
        code_id = hit.get("code_id", "")
        if code_id != "RCC":
            continue
        art_raw = str(hit.get("article", "")).strip()
        art_clean = re.sub(
            r"^(Article|Section|Art\.)\s+", "", art_raw, flags=re.IGNORECASE
        ).strip()
        canon = _canonical_provision_key(article_index, art_clean)
        if canon:
            valid_candidates.append(("RCC", canon))

    if not valid_candidates:
        _mark_processed(case["id"])
        return 0

    # PASS 2
    granular = pass2_granular(case, valid_candidates, article_index)
    if not granular:
        _mark_processed(case["id"])
        return 0

    final_links = []
    for link in granular:
        code_id = link.get("code_id", "")
        if code_id != "RCC":
            continue
        art_raw = str(link.get("article", "")).strip()
        art_clean = re.sub(
            r"^(Article|Section|Art\.)\s+", "", art_raw, flags=re.IGNORECASE
        ).strip()
        canon = _canonical_provision_key(article_index, art_clean)
        if not canon:
            continue
        entry = article_index["RCC"].get(canon)
        if not entry:
            continue
        para_idx = int(link.get("paragraph_index", -1))
        if para_idx >= entry["paragraph_count"]:
            para_idx = -1
        final_links.append({
            "provision_id": canon,
            "paragraph_index": para_idx,
            "summary": str(link.get("summary", ""))[:4000],
        })

    if dry_run:
        for lk in final_links:
            print(
                f"   [DRY] RCC Sec.{lk['provision_id']} "
                f"para{lk['paragraph_index']}: {lk['summary'][:60]}..."
            )
        return len(final_links)

    # COMMIT
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Idempotency: delete existing BP_68 links for this case
        cur.execute(
            "DELETE FROM codal_case_links WHERE case_id = %s AND statute_id = 'RCC' AND decided_under = 'BP_68'",
            (case["id"],),
        )
        for lk in final_links:
            cur.execute(
                """
                INSERT INTO codal_case_links
                    (case_id, statute_id, provision_id, target_paragraph_index,
                     specific_ruling, subject_area, is_resolved, decided_under, created_at)
                VALUES (%s, 'RCC', %s, %s, %s, 'Corporate Law', TRUE, 'BP_68', NOW())
                """,
                (
                    case["id"],
                    lk["provision_id"],
                    lk["paragraph_index"],
                    lk["summary"],
                ),
            )
        conn.commit()
        cur.close()
        print(f"   [saved] {len(final_links)} links -> {title}", flush=True)
    except Exception as exc:
        conn.rollback()
        print(f"   [ERR] DB error for {title}: {exc}", flush=True)
    finally:
        release(conn)
    _mark_processed(case["id"])

    return len(final_links)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

# Corporate-law keywords for pre-2019 case filter
_CORP_KEYWORDS = [
    'corporation code', 'batas pambansa 68', 'b.p. 68', 'b.p. blg. 68',
    'bp blg. 68', 'bp 68', 'corporate officer', 'board of directors',
    'piercing the corporate veil', 'derivative suit', 'stockholder',
    'corporate secretary', 'articles of incorporation',
]


def run(
    limit=None,
    start_year=None,
    end_year=None,
    workers=1,
    dry_run=True,
    target_ids=None,
    vertex_project=None,
    vertex_location=None,
):
    global client
    client = get_linker_genai_client(
        vertex_project=vertex_project,
        vertex_location=vertex_location,
    )
    from linker_genai_client import _vertex_project as _vp
    mode_str = f"Vertex AI (project={_vp})" if _vp else "AI Studio (API key)"

    print("\n" + "=" * 70)
    print(f"  BP 68 -> RCC 2-Pass Linker   Mode: {'DRY RUN' if dry_run else 'COMMIT'}")
    if dry_run:
        print("  (Dry run: no writes to codal_case_links.)")
    print(f"  GenAI backend: {mode_str}")
    print(f"  Model: {MODEL_NAME}")

    if target_ids:
        print(f"  Target IDs: {len(target_ids)} specific case(s)   Workers: {workers}")
    else:
        range_str = "ALL pre-2019"
        if start_year and end_year:
            range_str = f"{start_year}-{end_year}"
        elif start_year:
            range_str = f"{start_year}+"
        elif end_year:
            range_str = f"up to {end_year}"
        print(f"  Years: {range_str}   Workers: {workers}")
    print("=" * 70 + "\n")

    print("[*] Building RCC section index...")
    article_index = load_article_index()
    print(f"   RCC: {len(article_index['RCC'])} sections indexed\n")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    base_query = """
        SELECT id, short_title, main_doctrine, digest_ruling,
               digest_significance, digest_ratio, digest_facts, digest_issues
        FROM sc_decided_cases
        WHERE (main_doctrine IS NOT NULL
               OR digest_ruling IS NOT NULL
               OR digest_ratio IS NOT NULL
               OR digest_issues IS NOT NULL)
    """
    params = []

    if target_ids:
        placeholders = ",".join(["%s"] * len(target_ids))
        base_query += f" AND id IN ({placeholders})"
        params.extend(target_ids)
    else:
        # Default: pre-2019 corporate-law candidates not already BP_68-linked
        if end_year is None:
            end_year = 2018
        if start_year and end_year:
            base_query += " AND date BETWEEN %s AND %s"
            params += [f"{start_year}-01-01", f"{end_year}-12-31"]
        elif start_year:
            base_query += " AND date >= %s"
            params += [f"{start_year}-01-01"]
        else:
            base_query += " AND date <= %s"
            params += [f"{end_year}-12-31"]

        # Corporate-law keyword filter
        like_clauses = " OR ".join(
            "LOWER(full_text_md) LIKE %s" for _ in _CORP_KEYWORDS
        )
        base_query += f" AND ({like_clauses})"
        params.extend(f"%{k}%" for k in _CORP_KEYWORDS)

        if not dry_run:
            base_query += """
                AND NOT EXISTS (
                    SELECT 1 FROM bp68_processed_cases
                    WHERE case_id = sc_decided_cases.id
                )
            """

    base_query += " ORDER BY id DESC"
    if limit and not target_ids:
        base_query += " LIMIT %s"
        params.append(limit)

    cur.execute(base_query, params)
    cases = cur.fetchall()
    cur.close()
    release(conn)

    if not cases:
        print("[ok] No pending cases found.")
        return

    print(f"[*] {len(cases)} cases to analyse\n" + "=" * 70, flush=True)

    total_links = 0
    t0 = time.time()

    if workers > 1:
        progress = {"done": 0}
        prog_lock = threading.Lock()
        stop_hb = threading.Event()

        def _heartbeat_loop():
            interval = 30.0
            while not stop_hb.wait(interval):
                with prog_lock:
                    d = progress["done"]
                elapsed = time.time() - t0
                print(
                    f"  [...] heartbeat {elapsed:.0f}s: {d}/{len(cases)} cases finished "
                    f"(workers={workers})",
                    flush=True,
                )

        hb_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        hb_thread.start()
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(process_case, c, article_index, dry_run): c for c in cases}
                print(
                    f"[*] Pool running: {len(cases)} cases, {workers} workers — "
                    "first result may take 1-3 min.",
                    flush=True,
                )
                for i, fut in enumerate(as_completed(futs), 1):
                    c = futs[fut]
                    n = fut.result()
                    total_links += n
                    with prog_lock:
                        progress["done"] = i
                    print(
                        f"  [{i}/{len(cases)}] {c['short_title'][:45]} -> {n} links",
                        flush=True,
                    )
        finally:
            stop_hb.set()
    else:
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case['short_title'][:55]}", flush=True)
            total_links += process_case(case, article_index, dry_run)

    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print(f"  Cases evaluated : {len(cases)}")
    print(f"  Links created   : {total_links}")
    print(f"  Time elapsed    : {elapsed:.1f}s")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BP 68 -> RCC 2-Pass RAG Linker (pre-2019 corporate cases)"
    )
    parser.add_argument("--limit", type=int, help="Max cases to process")
    parser.add_argument("--year", type=int, help="Filter by single year")
    parser.add_argument("--start_year", type=int, help="Filter by start year")
    parser.add_argument("--end_year", type=int, default=2018, help="Filter by end year (default: 2018)")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    parser.add_argument("--commit", action="store_true", help="Write to DB (default: dry-run)")
    parser.add_argument(
        "--target-ids",
        type=str,
        dest="target_ids",
        help="Comma-separated sc_decided_cases.id values. Bypasses year filters.",
    )
    parser.add_argument(
        "--vertex-project",
        type=str,
        dest="vertex_project",
        default=None,
        help="GCP project for Vertex AI. If omitted, uses GOOGLE_CLOUD_PROJECT env var or AI Studio.",
    )
    parser.add_argument(
        "--vertex-location",
        type=str,
        dest="vertex_location",
        default=None,
        help="Vertex AI region. Defaults to GOOGLE_CLOUD_LOCATION env var (global for gemini-3-flash-preview).",
    )
    args = parser.parse_args()

    try:
        start_year = args.start_year
        end_year = args.end_year
        if args.year:
            start_year = args.year
            end_year = args.year

        target_ids = None
        if args.target_ids:
            target_ids = [int(x.strip()) for x in args.target_ids.split(",") if x.strip()]

        run(
            limit=args.limit,
            start_year=start_year,
            end_year=end_year,
            workers=args.workers,
            dry_run=not args.commit,
            target_ids=target_ids,
            vertex_project=args.vertex_project,
            vertex_location=args.vertex_location,
        )
    except KeyboardInterrupt:
        print("\n[stopped] Interrupted.")
    finally:
        if db_pool:
            db_pool.closeall()
