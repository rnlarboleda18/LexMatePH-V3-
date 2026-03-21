"""
Universal RPC Case Linker

This script analyzes ALL cases and identifies which RPC article sentences they interpret.
One case can link to multiple sentences across multiple articles.

Usage:
    python universal_rpc_linker.py --dry-run          # Preview only
    python universal_rpc_linker.py --commit           # Write to database
    python universal_rpc_linker.py --limit 10         # Test on 10 cases
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import time
from google import genai
import argparse

# --- CONFIG ---
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
MODEL_NAME = "gemini-3-flash-preview"
API_KEY = "REDACTED_API_KEY_HIDDEN"

client = genai.Client(api_key=API_KEY)

def load_rpc_articles(cur):
    """Load all RPC articles with their sentence structure"""
    cur.execute("""
        SELECT article_num, content_md 
        FROM rpc_codal 
        ORDER BY CAST(REGEXP_REPLACE(article_num, '\\D', '', 'g') AS INTEGER)
    """)
    
    articles = {}
    for row in cur.fetchall():
        article_num = row['article_num']
        content = row['content_md']
        
        # Split into sentences (simplified - split by paragraph for now)
        sentences = [s.strip() for s in content.split('\n\n') if s.strip()]
        
        articles[article_num] = {
            'content': content,
            'sentences': sentences,
            'sentence_count': len(sentences)
        }
    
    return articles

def analyze_case_rpc_links(case, rpc_articles):
    """
    Use AI to identify ALL RPC article+sentence interpretations in this case
    
    Returns:
        List of links: [
            {'article': '2', 'sentence_index': 0, 'summary': '...'},
            {'article': '4', 'sentence_index': 1, 'summary': '...'},
            ...
        ]
    """
    
    # Build RPC reference for AI
    article_list = "\n".join([
        f"Article {num}: {data['sentence_count']} sentences"
        for num, data in sorted(rpc_articles.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)[:50]  # First 50 articles
    ])
    
    prompt = f"""
You are a legal expert analyzing Philippine Supreme Court cases for RPC interpretations.

CASE DIGEST:
Title: {case['short_title']}
Main Doctrine: {case.get('main_doctrine') or 'N/A'}
Ratio Decidendi: {case.get('digest_ratio') or 'N/A'}
Significance: {case.get('digest_significance') or 'N/A'}
Ruling: {case.get('digest_ruling') or 'N/A'}

TASK:
Identify ALL Revised Penal Code (RPC) articles and specific sentences/paragraphs that this case INTERPRETS or APPLIES.

For each RPC article discussed:
1. Article number (e.g., "2", "4", "248")
2. Sentence/paragraph index (0-based), or -1 if it discusses the article generally
3. A concise summary (max 2 sentences) of how the case interprets that specific provision

IMPORTANT:
- Only include interpretations where the case actually clarifies or applies the RPC provision
- One case can have MULTIPLE links if it discusses multiple articles/sentences
- Exclude mere mentions or citations that don't interpret the law
- Be precise about which sentence is interpreted (count paragraphs separated by blank lines)

OUTPUT FORMAT (JSON):
{{
  "interpretations": [
    {{
      "article": "2",
      "sentence_index": 0,
      "summary": "Case clarifies that...",
      "confidence": 8
    }},
    {{
      "article": "4",
      "sentence_index": -1,
      "summary": "Discusses general applicability of...",
      "confidence": 7
    }}
  ]
}}

Return empty array if no RPC interpretations found.
"""
    
    try:
        time.sleep(0.5)  # Rate limiting
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        
        # Handle both dict ({"interpretations": [...]}) and list ([...]) formats
        if isinstance(result, list):
            interpretations = result
        else:
            interpretations = result.get('interpretations', [])
            
        # Validate sentence indices
        valid_interpretations = []
        for interp in interpretations:
            article = str(interp.get('article', ''))
            if not article: continue
            
            sentence_idx = int(interp.get('sentence_index', -1))
            
            # Validate article exists
            if article not in rpc_articles:
                continue
            
            # Validate sentence index
            if sentence_idx >= rpc_articles[article]['sentence_count']:
                sentence_idx = -1  # Invalid index, mark as general
            
            valid_interpretations.append({
                'article': article,
                'sentence_index': sentence_idx,
                'summary': interp.get('summary', 'Verified interpretation'),
                'confidence': interp.get('confidence', 5)
            })
        
        return valid_interpretations
        
    except Exception as e:
        print(f"    ⚠️  AI Error: {e}")
        return []

import concurrent.futures
from psycopg2 import pool

# Global pool (initialized in process_cases)
db_pool = None

def get_db_connection():
    return db_pool.getconn()

def return_db_connection(conn):
    db_pool.putconn(conn)

def process_single_case(case, rpc_articles, dry_run):
    """Worker function to process a single case"""
    links_created = 0
    case_title = case['short_title']
    
    try:
        interpretations = analyze_case_rpc_links(case, rpc_articles)
        
        if not interpretations:
            # print(f"   ⊘ {case_title[:30]}...: No RPC links")
            return 0
            
        # print(f"   ✅ {case_title[:30]}...: Found {len(interpretations)} links")
        
        # Prepare valid links
        valid_links = []
        for interp in interpretations:
            article = interp['article']
            sent_idx = interp['sentence_index']
            summary = interp['summary']
            
            valid_links.append({
                'case_id': case['id'],
                'article': article,
                'sentence_index': sent_idx,
                'summary': summary
            })

        if not dry_run and valid_links:
            conn = get_db_connection()
            try:
                write_cur = conn.cursor()
                
                # Idempotency: Delete existing links for this case
                write_cur.execute(
                    "DELETE FROM codal_case_links WHERE case_id = %s AND statute_id = 'RPC'",
                    (case['id'],)
                )
                
                # Insert new links
                for link in valid_links:
                    write_cur.execute("""
                        INSERT INTO codal_case_links (
                            case_id, statute_id, provision_id,
                            target_paragraph_index, specific_ruling, subject_area, is_resolved, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        link['case_id'],
                        'RPC',
                        link['article'],
                        link['sentence_index'],
                        link['summary'][:4000],
                        'Criminal Law',
                        True
                    ))
                
                conn.commit()
                write_cur.close()
                links_created = len(valid_links)
                print(f"   💾 Saved {links_created} links for {case_title[:40]}...")
                
            except Exception as e:
                conn.rollback()
                print(f"   ❌ DB Error for {case_title}: {e}")
            finally:
                return_db_connection(conn)
        
        return links_created

    except Exception as e:
        print(f"   ❌ Critical Error processing {case_title}: {e}")
        return 0

def process_cases(limit=None, dry_run=True, target_year=2025, workers=1):
    """Process all (or limited) cases and generate RPC links"""
    
    global db_pool
    
    print(f"\n{'='*70}")
    print(f"UNIVERSAL RPC CASE LINKER")
    print(f"Mode: {'DRY RUN' if dry_run else 'COMMIT TO DATABASE (INCREMENTAL)'}")
    print(f"Target Year: {target_year}")
    print(f"Workers: {workers}")
    print(f"{'='*70}\n")
    
    # Initialize connection pool
    try:
        db_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=workers + 2,
            dsn=DB_CONNECTION_STRING
        )
    except Exception as e:
        print(f"❌ Failed to create connection pool: {e}")
        return

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. Load RPC articles
        print("📚 Loading RPC articles...")
        rpc_articles = load_rpc_articles(cur)
        print(f"   Loaded {len(rpc_articles)} RPC articles\n")
        
        # 2. Get cases to process - FILTER FOR TARGET YEAR
        print("🔍 Fetching cases...")
        query = """
            SELECT 
                id, short_title, 
                main_doctrine, digest_ratio, 
                digest_ruling, digest_significance
            FROM sc_decided_cases
            WHERE (statutes_involved::text ILIKE '%%RPC%%'
               OR statutes_involved::text ILIKE '%%Revised Penal Code%%'
               OR statutes_involved::text ILIKE '%%Article%%')
              AND EXTRACT(YEAR FROM date) = %s
        """
        
        if not dry_run:
            query += """
                AND id NOT IN (
                    SELECT DISTINCT case_id 
                    FROM codal_case_links 
                    WHERE statute_id = 'RPC'
                )
            """
            
        query += " ORDER BY id"
        
        params = [target_year]
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cur.execute(query, tuple(params))
        cases = cur.fetchall()
        
        print(f"🔍 Found {len(cases)} pending RPC cases to analyze\n")
        
        # 3. Process cases in parallel
        print(f"🚀 Starting {workers} worker threads...")
        
        total_links = 0
        cases_processed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_case = {
                executor.submit(process_single_case, case, rpc_articles, dry_run): case 
                for case in cases
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_case):
                c = future_to_case[future]
                try:
                    links = future.result()
                    total_links += links
                    cases_processed += 1
                    
                    if cases_processed % 10 == 0:
                        print(f"   [Progress] {cases_processed}/{len(cases)} cases processed")
                        
                except Exception as exc:
                    print(f"   ❌ Generated an exception for {c['short_title']}: {exc}")
        
        # 4. Final Summary
        print(f"\n{'='*70}")
        print(f"PROCESSING SUMMARY")
        print(f"{'='*70}")
        print(f"Cases processed:           {cases_processed}")
        print(f"Total links created:       {total_links}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        if conn:
            return_db_connection(conn)
        if db_pool:
            db_pool.closeall()

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Universal RPC Case Linker')
    parser.add_argument('--limit', type=int, help='Limit number of cases to process')
    parser.add_argument('--year', type=int, default=2025, help='Year to process (default: 2025)')
    parser.add_argument('--workers', type=int, default=1, help='Number of parallel workers (default: 1)')
    parser.add_argument('mode', nargs='?', choices=['dry-run', 'commit'], default='dry-run', help='Mode: dry-run or commit')
    
    args = parser.parse_args()
    
    dry_run = args.mode != 'commit'
    
    print(f"\nMode: {'DRY RUN (review only)' if dry_run else 'COMMIT (will modify database)'}")
    print(f"Target Year: {args.year}")
    print(f"Workers: {args.workers}")
    
    if not dry_run:
        # Auto-confirm for queue script interaction
        pass 
    
    process_cases(limit=args.limit, dry_run=dry_run, target_year=args.year, workers=args.workers)

