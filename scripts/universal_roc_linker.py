"""
Universal ROC Case Linker
=========================
Dedicated 2-Pass RAG Linker that parses Case Digests and binds them to 
the correct Rules of Court (ROC) sections utilizing compound article_num keys.

How it works:
  PASS 1 (Router): Reads digest, lists suspected provisions (e.g., "Rule 110, Section 1").
  PASS 2 (Granular): Reads full texts of selected provisions, finds 0-based paragraph bounds.

Usage:
  python universal_roc_linker.py --limit 10           # Dry-run preview
  python universal_roc_linker.py --limit 10 --commit # Direct DB sync
"""

import os
import re
import json
import time
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DB_URL = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
MODEL_NAME = "gemini-3-flash-preview"
API_KEY = "REDACTED_API_KEY_HIDDEN"

genai.configure(api_key=API_KEY)

# ---------------------------------------------------------------------------
# PASS 1 – Router pass: involving ROC?
# ---------------------------------------------------------------------------

PASS1_SCHEMA = """
{
  "hits": [
    {"rule": "110", "section": "1"},
    {"rule": "112", "section": "3"}
  ]
}
"""

def call_gemini_with_retry(model_obj, prompt, max_retries=5):
    """Call Gemini with exponential backoff for 429 errors."""
    for i in range(max_retries):
        try:
            time.sleep(1 + i * 2) # Incremental wait
            response = model_obj.generate_content(prompt)
            return response
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower():
                wait_time = (2 ** i) * 5
                print(f"    ⏳ Rate limited (429). Waiting {wait_time}s before retry {i+1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            raise exc
    return None

def pass1_route(case: dict) -> list:
    """Ask AI to read digest and lists corresponding Rules and Sections found."""
    prompt = f"""
You are a Philippine legal expert. Analyse the Supreme Court case digest below 
and list every specific Rules of Court (ROC) provision it INTERPRETS or APPLIES.

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or 'N/A'}
Issues: {case.get('digest_issues') or 'N/A'}
Doctrine: {case.get('main_doctrine') or 'N/A'}
Ratio: {case.get('digest_ratio') or 'N/A'}
Ruling: {case.get('digest_ruling') or 'N/A'}

TASK (CORE CONSIDERATION):
Your PRIMARY basis for identifying the correct Rule and Section are the **Issues** and the **Ratio Decidendi**. The Facts and Doctrine provide essential context but the binding legal link is found in the correspondence between the specific legal issues raised and the court's ratio.

NEGATIVE CONSTRAINTS (CRITICAL):
- **DO NOT** link to **Rule 1, Section 6 (Liberal Construction)** just because the court mentions "substantial justice," "liberal construction," or remands the case. Only link if the Court is specifically interpreting the standard of construction for the Rules themselves.
- **DO NOT** link to general procedural terms (e.g., "Petition for Review," "Remand") unless a specific ROC provision governing that procedure is being explicitly construed or applied to resolve a procedural dispute.
- If the case is purely substantive (e.g., Civil Code easement, Penal Code elements) and only mentions ROC provisions as a standard vehicle for the remedy without interpreting them, return an empty hits JSON.

Return a JSON list of provision hits containing "rule" and "section" strings.
Example: Rule 110, Section 1 -> {{"rule": "110", "section": "1"}}

OUTPUT ONLY JSON:
{PASS1_SCHEMA}
"""
    try:
        print(f"    [Pass1] Calling Gemini for {case.get('short_title', 'case')[:30]}...")
        model_obj = genai.GenerativeModel(MODEL_NAME)
        response = call_gemini_with_retry(model_obj, prompt)
        if not response:
             return []
        print("    [Pass1] Gemini response received.")
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data.get("hits", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"    ⚠️  PASS-1 error: {exc}")
        return []

# ---------------------------------------------------------------------------
# PASS 2 – Granular paragraph Indexing
# ---------------------------------------------------------------------------

PASS2_SCHEMA = """
{
  "links": [
    {
      "rule_section_label": "Rule 110, Section 1",
      "paragraph_index": -1,
      "summary": "..."
    }
  ]
}
"""

def pass2_granular(case: dict, candidates: list, article_index: dict) -> list:
    """Identify exact 0-based paragraph index given the full Section text bounding frames."""
    if not candidates:
        return []

    article_blocks = []
    for label in candidates:
        entry = article_index.get(label)
        if entry:
            article_blocks.append(f"[{label}]:\n{entry['content']}")

    if not article_blocks:
        return []

    prompt = f"""
You are a Philippine legal expert finalizing a jurisprudence database for Remedial Law.

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or ''}
Issues: {case.get('digest_issues') or ''}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}

CANDIDATE ROC PROVISIONS FULL-TEXT:
{"\n\n---\n\n".join(article_blocks)}

TASK:
For each provision, confirm interpretative application and identify:
1. Exact 0-based paragraph index (Starting from 0: count fully separated blank line breaks).
   **PRIORITY**: Align the case **Issues** and **Ratio** with the specific paragraph of the provision. Use the **Facts** to verify that the application matches the original context.
   **STRICT CONFIRMATION**: If the case only refers to the provision in passing or as a general procedural vehicle (like Rule 1, Section 6 for "substantial justice") without a substantive discussion of its specific text, DO NOT include it in the links.
2. Concise 1-2 sentence ruling summary holding.

OUTPUT ONLY JSON:
{PASS2_SCHEMA}
"""
    try:
        model_obj = genai.GenerativeModel(MODEL_NAME)
        response = call_gemini_with_retry(model_obj, prompt)
        if not response:
             return []
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data.get("links", []) if isinstance(data, dict) else []
    except Exception as exc:
         print(f"    ⚠️  PASS-2 error: {exc}")
         return []

# ---------------------------------------------------------------------------
# Processing Frame
# ---------------------------------------------------------------------------

def load_roc_index(cur) -> dict:
    """Load all articles for ROC mapping compound identifiers accurately."""
    cur.execute("SELECT rule_section_label, section_content FROM roc_codal")
    index = {}
    for row in cur.fetchall():
        label = str(row['rule_section_label']).strip()
        text = str(row['section_content'] or "")
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        index[label] = {
            "content": text,
            "paragraph_count": len(paragraphs)
        }
    return index

from psycopg2 import pool

# Global pool
db_pool = None

def get_db_connection():
    return db_pool.getconn()

def return_db_connection(conn):
    db_pool.putconn(conn)

def process_single_case(case, index, dry_run):
    """Worker function to process a single case"""
    links_created = 0
    title = case.get("short_title", str(case["id"]))[:50]
    
    try:
        # PASS 1
        hits = pass1_route(case)
        valid_candidates = []
        for h in hits:
            f_num = f"Rule {h.get('rule')}, Section {h.get('section')}"
            if f_num in index:
                valid_candidates.append(f_num)

        if not valid_candidates:
            return 0

        # PASS 2
        granular = pass2_granular(case, valid_candidates, index)
        if not granular:
            return 0

        final_links = []
        for lk in granular:
            label = str(lk.get('rule_section_label') or lk.get('article_num')).strip()
            if label not in index:
                 continue
            para_idx = int(lk.get('paragraph_index', -1))
            if para_idx >= index[label]['paragraph_count']:
                 para_idx = -1
            final_links.append({
                "provision_id": label,
                "paragraph_index": para_idx,
                "summary": str(lk.get('summary', ''))[:4000]
            })

        if not dry_run and final_links:
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM codal_case_links WHERE case_id = %s AND statute_id = 'ROC'", (case['id'],))
                for lk in final_links:
                     cur.execute("""
                         INSERT INTO codal_case_links (
                             case_id, statute_id, provision_id, target_paragraph_index, 
                             specific_ruling, subject_area, is_resolved, created_at
                         ) VALUES (%s, 'ROC', %s, %s, %s, 'Remedial Law', TRUE, NOW())
                     """, (case['id'], lk['provision_id'], lk['paragraph_index'], lk['summary']))
                conn.commit()
                cur.close()
                links_created = len(final_links)
                print(f"   💾 Saved {links_created} links for {title}...")
            except Exception as e:
                conn.rollback()
                print(f"   ❌ DB Commit Error for {title}: {e}")
            finally:
                return_db_connection(conn)
        elif dry_run:
            for lk in final_links:
                 print(f"   [DRY] ROC {lk['provision_id']} ¶{lk['paragraph_index']}: {lk['summary'][:60]}...")
            links_created = len(final_links)

        return links_created

    except Exception as e:
        print(f"   ❌ Critical Error processing {title}: {e}")
        return 0

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(limit=None, target_year=2025, workers=1, dry_run=True):
    global db_pool
    print("\n" + "=" * 70)
    print(f"  Universal ROC Case Linker   Mode: {'DRY RUN' if dry_run else 'COMMIT'}")
    print(f"  Target Year: {target_year}   Workers: {workers}")
    print("=" * 70 + "\n")

    try:
        db_pool = pool.ThreadedConnectionPool(1, workers + 5, dsn=DB_URL)
    except Exception as e:
        print(f"❌ Failed to create connection pool: {e}")
        return

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("[*] Loading ROC Articles index...")
    index = load_roc_index(cur)
    print(f"    Loaded {len(index)} Section configurations.\n")

    print("[*] Fetching cases potentially linked to ROC...")
    cur.execute("""
        SELECT id, short_title, main_doctrine, digest_ratio, digest_ruling, digest_facts, digest_issues
        FROM sc_decided_cases
        WHERE (statutes_involved::text ILIKE '%%Rules of Court%%' OR statutes_involved::text ILIKE '%%ROC%%')
          AND EXTRACT(YEAR FROM date) = %s
        ORDER BY id DESC
    """, (target_year,))
    cases = cur.fetchall()
    cur.close()
    return_db_connection(conn)

    if limit:
         cases = cases[:limit]

    if not cases:
         print("✅ No pending cases found.")
         db_pool.closeall()
         return

    print(f"🔍 Found {len(cases)} cases to analyze\n" + "=" * 70)

    total_links = 0
    cases_processed = 0
    
    if workers == 1:
         print("[*] Running in continuous synchronous setup...")
         for case in cases:
              total_links += process_single_case(case, index, dry_run)
         cases_processed = len(cases)
    else:
         with ThreadPoolExecutor(max_workers=workers) as pool_executor:
              future_to_case = {
                  pool_executor.submit(process_single_case, case, index, dry_run): case 
                  for case in cases
              }
              for future in as_completed(future_to_case):
                  c = future_to_case[future]
                  try:
                      n = future.result()
                      total_links += n
                      cases_processed += 1
                      if cases_processed % 5 == 0:
                           print(f"   [Progress] {cases_processed}/{len(cases)} cases evaluated")
                  except Exception as exc:
                      print(f"   ❌ Exception for {c.get('short_title', c['id'])}: {exc}")

    print("\n" + "=" * 70)
    print(f"  Cases evaluated : {cases_processed}")
    print(f"  Links created   : {total_links}")
    print("=" * 70)
    db_pool.closeall()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Max cases to process")
    parser.add_argument("--year", type=int, default=2025, help="Case year to analyze")
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker threads")
    parser.add_argument("--commit", action="store_true", help="Write to DB")
    args = parser.parse_args()

    run(limit=args.limit, target_year=args.year, workers=args.workers, dry_run=not args.commit)
