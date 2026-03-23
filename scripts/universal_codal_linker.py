"""
Universal Codal Case Linker

This script analyzes ALL cases and identifies which sentences of a specific Code they interpret.
One case can link to multiple sentences across multiple articles.

Usage:
    python universal_codal_linker.py --code CIV --limit 5 --commit
    python universal_codal_linker.py --code LAB --limit 5 --commit
    python universal_codal_linker.py --code CONST --limit 5 --commit
    python universal_codal_linker.py --code FAM --limit 5 --commit
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import time
from google import genai
import argparse
import concurrent.futures
from psycopg2 import pool

# --- CONFIG ---
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
MODEL_NAME = "gemini-3-flash-preview"
API_KEY = "REDACTED_API_KEY_HIDDEN"

client = genai.Client(api_key=API_KEY)
db_pool = None

CODE_CONFIGS = {
    'CIV': {
        'table': 'civ_codal',
        'name': 'Civil Code of the Philippines',
        'keywords': ['Civil Code', 'CIV', 'Article', 'New Civil Code'],
        'subject_area': 'Civil Law'
    },
    'LAB': {
        'table': 'labor_codal',
        'name': 'Labor Code of the Philippines',
        'keywords': ['Labor Code', 'LAB', 'Article', 'Labor'],
        'subject_area': 'Labor Law'
    },
    'CONST': {
        'table': 'const_codal',
        'name': '1987 Philippine Constitution',
        'keywords': ['Constitution', 'CONST', 'Article', 'Section'],
        'subject_area': 'Political Law',
        'sort_by_id': True
    },
    'FAM': {
        'table': 'civ_codal',
        'name': 'Family Code of the Philippines',
        'keywords': ['Family Code', 'FC', 'Article'],
        'subject_area': 'Civil Law',
        'where': "title_label ILIKE '%family%'"
    }
}

def get_db_connection():
    return db_pool.getconn()

def return_db_connection(conn):
    db_pool.putconn(conn)

def load_codal_articles(cur, config):
    """Load all articles for the specified code with their sentence structure"""
    table = config['table']
    
    where_clause = ""
    if 'where' in config:
        where_clause = f"WHERE {config['where']}"
    
    if config.get('sort_by_id'):
        order_clause = "ORDER BY id ASC"
    else:
        order_clause = """
        ORDER BY 
            CAST(REGEXP_REPLACE(article_num, '\\D', '', 'g') AS INTEGER),
            article_num ASC
        """
        
    cur.execute(f"""
        SELECT article_num, content_md 
        FROM {table} 
        {where_clause}
        {order_clause}
    """)
    
    articles = {}
    for row in cur.fetchall():
        article_num = row['article_num']
        content = row['content_md']
        
        # Split into sentences (simplified - split by paragraph for now)
        sentences = [s.strip() for s in content.split('\\n\\n') if s.strip()]
        
        articles[article_num] = {
            'content': content,
            'sentences': sentences,
            'sentence_count': len(sentences)
        }
    
    return articles

def analyze_case_links(case, articles_dict, config, code_id):
    """Use AI to identify ALL interpretation links in this case"""
    
    code_name = config['name']
    
    # Build reference for AI
    article_list_str = "\\n".join([
        f"Article/Section {num}: {data['sentence_count']} paragraphs/sentences"
        for num, data in sorted(articles_dict.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)[:50] 
    ])
    
    prompt = f"""
You are a legal expert analyzing Philippine Supreme Court cases for {code_name} interpretations.

CASE DIGEST:
Title: {case['short_title']}
Main Doctrine: {case.get('main_doctrine') or 'N/A'}
Ratio Decidendi: {case.get('digest_ratio') or 'N/A'}
Significance: {case.get('digest_significance') or 'N/A'}
Ruling: {case.get('digest_ruling') or 'N/A'}

TASK:
Identify ALL provisions of the {code_name} and specific sentences/paragraphs that this case INTERPRETS or APPLIES.

For each provision discussed:
1. Article or Section number (e.g., "2", "4", "248")
2. Sentence/paragraph index (0-based), or -1 if it discusses the provision generally
3. A concise summary (max 2 sentences) of how the case interprets that specific provision

IMPORTANT:
- Only include interpretations where the case actually clarifies or applies the {code_name}
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
    }}
  ]
}}

Return empty array if no {code_name} interpretations found.
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
        
        if isinstance(result, list):
            interpretations = result
        else:
            interpretations = result.get('interpretations', [])
            
        valid_interpretations = []
        for interp in interpretations:
            article = str(interp.get('article', ''))
            if not article: continue
            
            sentence_idx = int(interp.get('sentence_index', -1))
            
            if article not in articles_dict:
                continue
            
            if sentence_idx >= articles_dict[article]['sentence_count']:
                sentence_idx = -1
            
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

def process_single_case(case, articles_dict, config, code_id, dry_run):
    """Worker function to process a single case"""
    links_created = 0
    case_title = case['short_title']
    
    try:
        interpretations = analyze_case_links(case, articles_dict, config, code_id)
        
        if not interpretations:
            return 0
            
        valid_links = []
        for interp in interpretations:
            valid_links.append({
                'case_id': case['id'],
                'article': interp['article'],
                'sentence_index': interp['sentence_index'],
                'summary': interp['summary']
            })

        if not dry_run and valid_links:
            conn = get_db_connection()
            try:
                write_cur = conn.cursor()
                
                # Idempotency
                write_cur.execute(
                    "DELETE FROM codal_case_links WHERE case_id = %s AND statute_id = %s",
                    (case['id'], code_id)
                )
                
                for link in valid_links:
                    write_cur.execute("""
                        INSERT INTO codal_case_links (
                            case_id, statute_id, provision_id,
                            target_paragraph_index, specific_ruling, subject_area, is_resolved, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        link['case_id'],
                        code_id,
                        link['article'],
                        link['sentence_index'],
                        link['summary'][:4000],
                        config['subject_area'],
                        True
                    ))
                
                conn.commit()
                write_cur.close()
                links_created = len(valid_links)
                print(f"   [{code_id}] 💾 Saved {links_created} links for {case_title[:40]}...")
                
            except Exception as e:
                conn.rollback()
                print(f"   ❌ DB Error for {case_title}: {e}")
            finally:
                return_db_connection(conn)
        
        return links_created

    except Exception as e:
        print(f"   ❌ Critical Error processing {case_title}: {e}")
        return 0

def process_cases(code_id, limit=None, dry_run=True, target_year=2025, workers=1):
    global db_pool
    config = CODE_CONFIGS[code_id]
    
    print(f"\\n{'='*70}")
    print(f"UNIVERSAL CODAL CASE LINKER: {code_id} ({config['name']})")
    print(f"Mode: {'DRY RUN' if dry_run else 'COMMIT'}")
    print(f"Target Year: {target_year}")
    print(f"Workers: {workers}")
    print(f"{'='*70}\\n")
    
    try:
        db_pool = pool.ThreadedConnectionPool(1, workers + 2, dsn=DB_CONNECTION_STRING)
    except Exception as e:
        print(f"❌ Failed to create connection pool: {e}")
        return

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print(f"📚 Loading {code_id} articles from {config['table']}...")
        articles_dict = load_codal_articles(cur, config)
        print(f"   Loaded {len(articles_dict)} articles\\n")
        
        print("🔍 Fetching cases...")
        # Build flexible ILIKE conditions
        kw_conditions = []
        for kw in config['keywords']:
            kw_conditions.append(f"statutes_involved::text ILIKE '%%{kw}%%'")
        kw_where = " OR ".join(kw_conditions)
        
        query = f"""
            SELECT 
                id, short_title, 
                main_doctrine, digest_ratio, 
                digest_ruling, digest_significance
            FROM sc_decided_cases
            WHERE ({kw_where})
              AND EXTRACT(YEAR FROM date) = %s
        """
        
        if not dry_run:
            query += f"""
                AND NOT EXISTS (
                    SELECT 1 
                    FROM codal_case_links 
                    WHERE case_id = sc_decided_cases.id
                      AND statute_id = '{code_id}'
                )
            """
            
        query += " ORDER BY id"
        
        params = [target_year]
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cur.execute(query, tuple(params))
        cases = cur.fetchall()
        
        print(f"🔍 Found {len(cases)} pending {code_id} cases to analyze\\n")
        
        if not cases:
            return
            
        total_links = 0
        cases_processed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_case = {
                executor.submit(process_single_case, case, articles_dict, config, code_id, dry_run): case 
                for case in cases
            }
            
            for future in concurrent.futures.as_completed(future_to_case):
                c = future_to_case[future]
                try:
                    links = future.result()
                    total_links += links
                    cases_processed += 1
                except Exception as exc:
                    print(f"   ❌ Generated an exception for {c['short_title']}: {exc}")
        
        print(f"\\n{'='*70}")
        print(f"[{code_id}] SUMMARY")
        print(f"Cases processed:           {cases_processed}")
        print(f"Total links created:       {total_links}")
        print(f"{'='*70}")
        
    finally:
        if conn: return_db_connection(conn)
        if db_pool: db_pool.closeall()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Universal Codal Case Linker')
    parser.add_argument('--code', type=str, required=True, choices=CODE_CONFIGS.keys(), help='Code ID to process')
    parser.add_argument('--limit', type=int, help='Limit number of cases to process')
    parser.add_argument('--year', type=int, default=2025, help='Year to process (default: 2025)')
    parser.add_argument('--workers', type=int, default=1, help='Number of parallel workers (default: 1)')
    parser.add_argument('--commit', action='store_true', help='Write to database (default is dry-run)')
    
    args = parser.parse_args()
    process_cases(args.code, limit=args.limit, dry_run=not args.commit, target_year=args.year, workers=args.workers)
