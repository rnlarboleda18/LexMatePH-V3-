"""
unified_codal_linker.py
========================
Token-Efficient 2-Pass RAG Linker for Philippine Legal Codes.

GenAI: Vertex AI only (ADC), via ``linker_genai_client`` — set ``GOOGLE_CLOUD_PROJECT`` and authenticate.

How it works:
  PASS 1 (Router): The AI reads the case digest ONCE and returns a list of
                   (code_id, provision id) pairs it thinks are relevant.
  DB Fetch:        The script fetches the FULL TEXT only of those provisions
                   (RPC: articles; RCC: sections — DB column is still ``article_num``).
  PASS 2 (Granular): The AI re-reads the case digest + the provision texts
                   and identifies the exact 0-based paragraph index.

Dry run (default) prints proposed links only — it does **not** write to
``codal_case_links`` or codal tables. Use ``--commit`` to persist.

This saves tokens vs the old approach (which fed ALL provisions each time) while
still achieving paragraph-level granularity.

Usage:
  python unified_codal_linker.py --limit 5 --commit
  python unified_codal_linker.py --year 2024 --workers 5 --commit
  python unified_codal_linker.py --statutes CIV,LAB,CONST,FAM --limit 10  # optional: other codes

Default statutes are RPC and RCC only. Use ``--statutes`` to add or replace the set.
"""

import os
import re
import json
import time
import argparse
import psycopg2
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
client = get_linker_genai_client()
db_pool: ThreadedConnectionPool = None  # type: ignore

# Full registry (use ``--statutes`` to enable CIV/LAB/CONST/FAM). Default run = RPC + RCC only.
FULL_CODE_CONFIGS: dict = {
    "CIV": {
        "table": "civ_codal",
        "name": "Civil Code of the Philippines",
        "subject_area": "Civil Law",
    },
    "LAB": {
        "table": "labor_codal",
        "name": "Labor Code of the Philippines",
        "subject_area": "Labor Law",
    },
    "CONST": {
        "table": "consti_codal",
        "name": "1987 Philippine Constitution",
        "subject_area": "Political Law",
        "sort_by_id": True,
    },
    "FAM": {
        "table": "fc_codal",
        "name": "Family Code of the Philippines",
        "subject_area": "Civil Law",
        "provision_id_transform": lambda num: num.split('-')[-1] if '-' in num else num,
    },
    "RPC": {
        "table": "rpc_codal",
        "name": "Revised Penal Code of the Philippines",
        "subject_area": "Criminal Law",
        "where": "book IS NOT NULL",
    },
    "RCC": {
        "table": "rcc_codal",
        "name": "Revised Corporation Code of the Philippines",
        "subject_area": "Corporate Law",
    },
}

DEFAULT_LINKER_STATUTES: tuple = ("RPC", "RCC")

# Active set — reassigned at the start of each ``run()`` (default: RPC, RCC).
CODE_CONFIGS: dict = {
    k: FULL_CODE_CONFIGS[k] for k in DEFAULT_LINKER_STATUTES
}

_STATUTE_PROMPT_LINES: dict = {
    "CIV": '  CIV: Civil Code of the Philippines — format: bare article number (e.g. "1306")',
    "LAB": '  LAB: Labor Code of the Philippines — format: bare article number (e.g. "301")',
    "CONST": (
        "  CONST: 1987 Philippine Constitution — format: Article-Section like \"III-1\" "
        '(Article III Section 1), "VIII-15" (Article VIII Section 15)'
    ),
    "FAM": '  FAM: Family Code of the Philippines — format: bare article number (e.g. "36")',
    "RPC": (
        '  RPC: Revised Penal Code — format: bare article number as in the code (e.g. "6", "48")'
    ),
    "RCC": (
        "  RCC: Revised Corporation Code — the Code has **Sections**, not Articles. "
        'Format: bare section number as stored (e.g. "23"); omit the word "Section". '
        'JSON still uses the field name "article" for every code; for RCC its value is the section number.'
    ),
}

_STATUTE_ORDER: tuple = ("CIV", "LAB", "CONST", "FAM", "RPC", "RCC")


def _codes_detail_prompt() -> str:
    lines = [
        _STATUTE_PROMPT_LINES[cid]
        for cid in _STATUTE_ORDER
        if cid in CODE_CONFIGS and cid in _STATUTE_PROMPT_LINES
    ]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    global db_pool
    if db_pool is None:
        db_pool = ThreadedConnectionPool(1, 50, dsn=DB_URL)
    return db_pool.getconn()


def release(conn):
    if db_pool:
        db_pool.putconn(conn)


# ---------------------------------------------------------------------------
# Pre-load article index (article_num + paragraph count, no full text yet)
# ---------------------------------------------------------------------------

def load_article_index() -> dict:
    """
    Returns a nested dict:
        index[code_id][provision_key] = {
            'content': ...,
            'paragraph_count': N,
        }
    For CONST, provision_key is the section_label (e.g. 'SECTION 2') —
    the same value that const.py API sends to the frontend as article_num.
    For other codes, the key is the bare ``article_num`` after stripping labels (e.g. CIV ``1306``).
    RCC uses the same DB column but legally those are **section** numbers.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    index: dict = {}

    for code_id, cfg in CODE_CONFIGS.items():
        index[code_id] = {}
        table = cfg["table"]
        where = f"WHERE {cfg['where']}" if "where" in cfg else ""

        if code_id == "CONST":
            # Use raw article_num (e.g. 'III-1') — unique and what const.py stores.
            # section_label ('SECTION 2') is ambiguous (20 dupes across articles).
            cur.execute(
                f"SELECT article_num, content_md FROM {table} {where}"
            )
            for row in cur.fetchall():
                art_num = str(row[0] or "").strip()
                if not art_num:
                    continue
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][art_num] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }
        elif code_id == "FAM":
            # fc_codal uses article_num like 'FC-IX-220'; match FC API key (last segment).
            transform = cfg.get("provision_id_transform", lambda x: x)
            cur.execute(
                f"SELECT article_num, content_md FROM {table} {where}"
            )
            for row in cur.fetchall():
                raw_num = str(row[0] or "").strip()
                provision_key = transform(raw_num)
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][provision_key] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }
        else:
            cur.execute(f"SELECT article_num, content_md FROM {table} {where}")
            for row in cur.fetchall():
                raw_num = str(row[0])
                clean_num = re.sub(
                    r"^(Article|Section|Art\.)\s+", "", raw_num, flags=re.IGNORECASE
                ).strip()
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][clean_num] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }

    cur.close()
    release(conn)
    return index


# ---------------------------------------------------------------------------
# PASS 1 – Router pass: which code + provision numbers does this case touch?
# ---------------------------------------------------------------------------

PASS1_SCHEMA = """
{
  "hits": [
    {"code_id": "RPC", "article": "6"},
    {"code_id": "RCC", "article": "23"}
  ]
}
"""


def pass1_route(case: dict) -> list:
    """
    Ask the AI: 'does this case interpret a provision from any of the configured codes?
    If so, which code_id and provision identifier?'
    Returns a list of dicts: [{'code_id': 'RPC', 'article': '6'}, ...]
    (JSON field remains ``article`` for all codes; RCC values are section numbers.)
    """
    prompt = f"""
You are a Philippine legal expert. Analyse the case digest below and list every
specific provision from these Philippine statutes that this case INTERPRETS or APPLIES
(not just mentions).

AVAILABLE STATUTES AND NUMBERING FORMAT:
{_codes_detail_prompt()}

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or 'N/A'}
Issues: {case.get('digest_issues') or 'N/A'}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}
Ruling: {case.get('digest_ruling') or ''}
Significance: {case.get('digest_significance') or ''}

TASK (CORE CONSIDERATION):
Your PRIMARY basis for identifying the correct statute and provision are the **Issues** and the **Ratio Decidendi**. The Facts and Doctrine provide essential context but the binding legal link is found in the correspondence between the specific legal issues raised and the court's reasoning.

RULES:
- Output ONLY valid code_id values from the list above.
- Use the exact numbering format shown per code (RPC: article numbers; RCC: **section** numbers only — the RCC has no "Articles").
- Each hit must use JSON key **"article"** even for RCC; the value is still the bare section number string.
  Constitution example: "III-2" means Article III, Section 2.
- If no provision from these statutes is interpreted, return {{"hits": []}}

OUTPUT FORMAT (JSON only):
{PASS1_SCHEMA}
"""

    try:
        time.sleep(0.5)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai.types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(response.text)
        return data.get("hits", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"    ⚠️  PASS-1 error: {exc}")
        return []


# ---------------------------------------------------------------------------
# PASS 2 – Granular pass: exact paragraph index given the full provision text
# ---------------------------------------------------------------------------

PASS2_SCHEMA = """
{
  "links": [
    {
      "code_id": "RPC",
      "article": "6",
      "paragraph_index": -1,
      "summary": "..."
    }
  ]
}
"""


def _candidate_heading(code_id: str, art_num: str) -> str:
    """RCC provisions are labeled Section in the product; others use Article."""
    if code_id == "RCC":
        return f"[{code_id}] Section {art_num}:"
    return f"[{code_id}] Article {art_num}:"


def pass2_granular(case: dict, candidates: list, article_index: dict) -> list:
    """
    For each (code_id, article) candidate, we already have the full text.
    Build one combined prompt for all of them and ask the AI to:
      1. Confirm whether the case really interprets that provision.
      2. Identify the exact 0-based paragraph index (or -1 for general).
      3. Write a concise ruling summary.
    """
    if not candidates:
        return []

    # Build article text block
    article_blocks = []
    for code_id, art_num in candidates:
        entry = article_index[code_id].get(art_num)
        if not entry:
            continue
        article_blocks.append(
            f"{_candidate_heading(code_id, art_num)}\n{entry['content'][:800]}"
        )

    if not article_blocks:
        return []

    articles_section = "\n\n---\n\n".join(article_blocks)

    prompt = f"""
You are a Philippine legal expert finalising a jurisprudence database.

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or ''}
Issues: {case.get('digest_issues') or ''}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}
Ruling: {case.get('digest_ruling') or ''}

CANDIDATE PROVISIONS:
{articles_section}

For EACH candidate provision above:
1. Confirm whether the case truly interprets/applies it (include it only if yes).
2. Identify the exact 0-based paragraph that is discussed, or -1 if the ruling
   is about the provision in general (not a specific paragraph).
   Count paragraph breaks (blank lines) starting from 0.
   **PRIORITY**: Align the case **Issues** and **Ratio** with the specific paragraph of the provision. Use the **Facts** to verify that the application matches the original context.
3. Write a concise one-to-two sentence summary of the holding regarding that provision.

RULES:
- "article" = bare number/string as in the candidate heading (no 'Article' / 'Section' prefix).
- "paragraph_index" = integer (-1 for general).

OUTPUT (JSON only):
{PASS2_SCHEMA}
"""

    try:
        time.sleep(0.5)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai.types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(response.text)
        return data.get("links", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"    ⚠️  PASS-2 error: {exc}")
        return []


# ---------------------------------------------------------------------------
# Main per-case worker
# ---------------------------------------------------------------------------

def process_case(case: dict, article_index: dict, dry_run: bool) -> int:
    title = case.get("short_title", str(case["id"]))[:50]

    # ---- PASS 1 ----
    raw_hits = pass1_route(case)
    if not raw_hits:
        return 0

    # Validate hits against index (normalise article numbers)
    valid_candidates = []  # list of (code_id, normalised_art_num)
    for hit in raw_hits:
        code_id = hit.get("code_id", "")
        art_raw = str(hit.get("article", "")).strip()
        art_clean = re.sub(
            r"^(Article|Section|Art\.)\s+", "", art_raw, flags=re.IGNORECASE
        ).strip()

        if code_id not in article_index:
            continue
        if art_clean in article_index[code_id]:
            valid_candidates.append((code_id, art_clean))

    if not valid_candidates:
        return 0

    # ---- PASS 2 ----
    granular = pass2_granular(case, valid_candidates, article_index)
    if not granular:
        return 0

    # Validate and sanitise PASS-2 output
    final_links = []
    for link in granular:
        code_id = link.get("code_id", "")
        art_raw = str(link.get("article", "")).strip()
        art_clean = re.sub(
            r"^(Article|Section|Art\.)\s+", "", art_raw, flags=re.IGNORECASE
        ).strip()

        if code_id not in article_index:
            continue
        entry = article_index[code_id].get(art_clean)
        if not entry:
            continue

        para_idx = int(link.get("paragraph_index", -1))
        if para_idx >= entry["paragraph_count"]:
            para_idx = -1

        final_links.append({
            "code_id": code_id,
            "provision_id": art_clean,  # already in the correct API-matching format
            "paragraph_index": para_idx,
            "summary": str(link.get("summary", ""))[:4000],
            "subject_area": CODE_CONFIGS[code_id]["subject_area"],
        })

    if dry_run:
        for lk in final_links:
            prov = "Sec." if lk["code_id"] == "RCC" else "Art."
            print(
                f"   [DRY] {lk['code_id']} {prov}{lk['provision_id']} "
                f"¶{lk['paragraph_index']}: {lk['summary'][:60]}..."
            )
        return len(final_links)

    # ---- COMMIT ----
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Idempotency: delete existing links for this case across all codes
        cur.execute(
            "DELETE FROM codal_case_links WHERE case_id = %s AND statute_id = ANY(%s)",
            (case["id"], list(CODE_CONFIGS.keys())),
        )
        for lk in final_links:
            cur.execute(
                """
                INSERT INTO codal_case_links
                    (case_id, statute_id, provision_id, target_paragraph_index,
                     specific_ruling, subject_area, is_resolved, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW())
                """,
                (
                    case["id"],
                    lk["code_id"],
                    lk["provision_id"],
                    lk["paragraph_index"],
                    lk["summary"],
                    lk["subject_area"],
                ),
            )
        conn.commit()
        cur.close()
        print(
            f"   💾 {len(final_links)} links → {title}"
        )
    except Exception as exc:
        conn.rollback()
        print(f"   ❌ DB error for {title}: {exc}")
    finally:
        release(conn)

    return len(final_links)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(limit=None, start_year=None, end_year=None, workers=1, dry_run=True, statutes=None):
    print("\n" + "=" * 70)
    print(f"  Unified 2-Pass RAG Linker   Mode: {'DRY RUN' if dry_run else 'COMMIT'}")
    if dry_run:
        print("  (Dry run: no writes to codal_case_links or codal body tables.)")
    print(f"  Vertex model: {MODEL_NAME}")

    global CODE_CONFIGS
    if statutes:
        filtered_configs = {
            cid: FULL_CODE_CONFIGS[cid] for cid in statutes if cid in FULL_CODE_CONFIGS
        }
        if not filtered_configs:
            print(f"❌ Error: None of the provided statutes {statutes} are configured.")
            return
        CODE_CONFIGS = filtered_configs
    else:
        CODE_CONFIGS = {k: FULL_CODE_CONFIGS[k] for k in DEFAULT_LINKER_STATUTES}
    print(f"[*] Statutes: {', '.join(CODE_CONFIGS.keys())}")
    
    range_str = "ALL"
    if start_year and end_year:
        range_str = f"{start_year}-{end_year}"
    elif start_year:
        range_str = f"{start_year}+"
    elif end_year:
        range_str = f"up to {end_year}"
        
    print(f"  Years: {range_str}   Workers: {workers}")
    print("=" * 70 + "\n")

    # Load provision index once (column name article_num; RCC = sections)
    print("[*] Building provision index from codal tables...")
    article_index = load_article_index()
    total_arts = sum(len(v) for v in article_index.values())
    for cid, arts in article_index.items():
        unit = "sections" if cid == "RCC" else "articles"
        print(f"   {cid}: {len(arts)} {unit}")
    print(f"   Total: {total_arts} provisions indexed\n")

    # Fetch cases
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT id, short_title, main_doctrine, digest_ruling,
               digest_significance, digest_ratio, digest_facts, digest_issues
        FROM sc_decided_cases
        WHERE (main_doctrine IS NOT NULL
               OR digest_ruling IS NOT NULL
               OR digest_ratio IS NOT NULL
               OR digest_issues IS NOT NULL)
    """
    params = []

    if start_year and end_year:
        query += " AND date BETWEEN %s AND %s"
        params += [f"{start_year}-01-01", f"{end_year}-12-31"]
    elif start_year:
        query += " AND date >= %s"
        params += [f"{start_year}-01-01"]
    elif end_year:
        query += " AND date <= %s"
        params += [f"{end_year}-12-31"]

    if not dry_run:
        # If specific statutes are requested, only exclude links for those statutes
        # Otherwise, exclude any case that has any links for any configured statute
        target_statutes = list(CODE_CONFIGS.keys())
        query += """
            AND NOT EXISTS (
                SELECT 1 FROM codal_case_links
                WHERE case_id = sc_decided_cases.id
                  AND statute_id = ANY(%s)
            )
        """
        params.append(target_statutes)

    query += " ORDER BY id DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)

    cur.execute(query, params)
    cases = cur.fetchall()
    cur.close()
    release(conn)

    if not cases:
        print("✅ No pending cases found.")
        return

    print(f"🔍 {len(cases)} cases to analyse\n" + "=" * 70)

    total_links = 0
    t0 = time.time()

    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(process_case, c, article_index, dry_run): c for c in cases}
            for i, fut in enumerate(as_completed(futs), 1):
                c = futs[fut]
                n = fut.result()
                total_links += n
                print(f"  [{i}/{len(cases)}] {c['short_title'][:45]} → {n} links")
    else:
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case['short_title'][:55]}")
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
    parser = argparse.ArgumentParser(description="Unified 2-Pass RAG Codal Linker")
    parser.add_argument("--limit", type=int, help="Max cases to process")
    parser.add_argument("--year", type=int, help="Filter by case year")
    parser.add_argument("--start_year", type=int, help="Filter by start year")
    parser.add_argument("--end_year", type=int, help="Filter by end year")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    parser.add_argument("--commit", action="store_true", help="Write to DB (default: dry-run)")
    parser.add_argument(
        "--statutes",
        type=str,
        help=(
            "Comma-separated code IDs (default: RPC,RCC). "
            "e.g. CIV,LAB,CONST,FAM,RPC,RCC"
        ),
    )
    args = parser.parse_args()

    try:
        # Resolve year range
        start_year = args.start_year
        end_year = args.end_year
        if args.year:
            start_year = args.year
            end_year = args.year

        statutes = (
            [s.strip() for s in args.statutes.split(",") if s.strip()]
            if args.statutes
            else None
        )

        run(
            limit=args.limit,
            start_year=start_year,
            end_year=end_year,
            workers=args.workers,
            dry_run=not args.commit,
            statutes=statutes,
        )
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
    finally:
        if db_pool:
            db_pool.closeall()
