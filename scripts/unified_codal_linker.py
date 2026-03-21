"""
unified_codal_linker.py
========================
Token-Efficient 2-Pass RAG Linker for Philippine Legal Codes.

How it works:
  PASS 1 (Router): The AI reads the case digest ONCE and returns a list of
                   (code_id, article_num) pairs it thinks are relevant.
  DB Fetch:        The script fetches the FULL TEXT only of those specific
                   articles from the database.
  PASS 2 (Granular): The AI re-reads the case digest + the actual article texts
                   and identifies the exact 0-based paragraph index.

This saves tokens vs the old approach (which fed ALL articles each time) while
still achieving paragraph-level granularity.

Usage:
  python unified_codal_linker.py --limit 5 --commit
  python unified_codal_linker.py --year 2024 --workers 5 --commit
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

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DB_URL = (
    os.environ.get("DB_CONNECTION_STRING")
    or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
)
MODEL_NAME = "gemini-2.0-flash"
API_KEY = "REDACTED_API_KEY_HIDDEN"

client = genai.Client(api_key=API_KEY)
db_pool: ThreadedConnectionPool = None  # type: ignore

# Code configuration – table, human name, how to sort, optional WHERE filter
CODE_CONFIGS: dict = {
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
        "table": "const_codal",
        "name": "1987 Philippine Constitution",
        "subject_area": "Political Law",
        "sort_by_id": True,
    },
    "FAM": {
        "table": "const_codal",
        "name": "Family Code of the Philippines",
        "subject_area": "Civil Law",
        "where": "book_code = 'FC'",
        # The FC API maps article_num like 'FC-IX-220' -> '220' (last segment after '-')
        "provision_id_transform": lambda num: num.split('-')[-1] if '-' in num else num,
    },
    # RPC is excluded — its links are already processed by universal_rpc_linker.py
}

CODES_SUMMARY = "\n".join(
    f"  {cid}: {cfg['name']}" for cid, cfg in CODE_CONFIGS.items()
)

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
    For all other codes, it is the bare article_num (e.g. '1306').
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
            # FC articles in const_codal use article_num like 'FC-IX-220'.
            # The FC API sends article_num.split('-')[-1] = '220' to the frontend.
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
# PASS 1 – Router pass: which code + article numbers does this case touch?
# ---------------------------------------------------------------------------

PASS1_SCHEMA = """
{
  "hits": [
    {"code_id": "CIV", "article": "1306"},
    {"code_id": "CONST", "article": "III-1"}
  ]
}
"""

# Hint shown in PASS 1 prompt so AI knows the expected format per code
CODES_DETAIL = (
    "  CIV: Civil Code of the Philippines — format: bare article number (e.g. \"1306\")\n"
    "  LAB: Labor Code of the Philippines — format: bare article number (e.g. \"301\")\n"
    "  CONST: 1987 Philippine Constitution — format: Article-Section like \"III-1\" "
    "(Article III Section 1), \"VIII-15\" (Article VIII Section 15)\n"
    "  FAM: Family Code of the Philippines — format: bare article number (e.g. \"36\")"
)


def pass1_route(case: dict) -> list:
    """
    Ask the AI: 'does this case interpret a provision from any of the five codes?
    If so, which code_id and article number?'
    Returns a list of dicts: [{'code_id': 'CIV', 'article': '1306'}, ...]
    """
    prompt = f"""
You are a Philippine legal expert. Analyse the case digest below and list every
specific provision from these Philippine statutes that this case INTERPRETS or APPLIES
(not just mentions).

AVAILABLE STATUTES AND THEIR ARTICLE FORMAT:
{CODES_DETAIL}

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or 'N/A'}
Issues: {case.get('digest_issues') or 'N/A'}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}
Ruling: {case.get('digest_ruling') or ''}
Significance: {case.get('digest_significance') or ''}

TASK (CORE CONSIDERATION):
Your PRIMARY basis for identifying the correct statute and article are the **Issues** and the **Ratio Decidendi**. The Facts and Doctrine provide essential context but the binding legal link is found in the correspondence between the specific legal issues raised and the court's reasoning.

RULES:
- Output ONLY valid code_id values from the list above.
- Use the exact article format shown per code above.
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
# PASS 2 – Granular pass: exact paragraph index given the full article text
# ---------------------------------------------------------------------------

PASS2_SCHEMA = """
{
  "links": [
    {
      "code_id": "CIV",
      "article": "1306",
      "paragraph_index": -1,
      "summary": "..."
    }
  ]
}
"""


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
            f"[{code_id}] Article {art_num}:\n{entry['content'][:800]}"
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
- "article" = just the number, no "Article" prefix.
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
            print(
                f"   [DRY] {lk['code_id']} Art.{lk['provision_id']} "
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

    # Filter CODE_CONFIGS if statutes are provided
    global CODE_CONFIGS
    if statutes:
        filtered_configs = {cid: CODE_CONFIGS[cid] for cid in statutes if cid in CODE_CONFIGS}
        if not filtered_configs:
            print(f"❌ Error: None of the provided statutes {statutes} are configured.")
            return
        CODE_CONFIGS = filtered_configs
        print(f"[*] Targeting statutes: {', '.join(CODE_CONFIGS.keys())}")
    
    range_str = "ALL"
    if start_year and end_year:
        range_str = f"{start_year}-{end_year}"
    elif start_year:
        range_str = f"{start_year}+"
    elif end_year:
        range_str = f"up to {end_year}"
        
    print(f"  Years: {range_str}   Workers: {workers}")
    print("=" * 70 + "\n")

    # Load article index once
    print("[*] Building article index...")
    article_index = load_article_index()
    total_arts = sum(len(v) for v in article_index.values())
    for cid, arts in article_index.items():
        print(f"   {cid}: {len(arts)} articles")
    print(f"   Total: {total_arts} articles\n")

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
    parser.add_argument("--statutes", type=str, help="Comma-separated code IDs (e.g. CIV,LAB)")
    args = parser.parse_args()

    try:
        # Resolve year range
        start_year = args.start_year
        end_year = args.end_year
        if args.year:
            start_year = args.year
            end_year = args.year

        statutes = args.statutes.split(",") if args.statutes else None

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
