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
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
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
        interpretations = result.get('interpretations', [])
        
        # Validate sentence indices
        valid_interpretations = []
        for interp in interpretations:
            article = str(interp['article'])
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

def process_cases(limit=None, dry_run=True, target_year=2025):
    """Process all (or limited) cases and generate RPC links"""
    
    print(f"\n{'='*70}")
    print(f"UNIVERSAL RPC CASE LINKER")
    print(f"Mode: {'DRY RUN' if dry_run else 'COMMIT TO DATABASE'}")
    print(f"Target Year: {target_year}")
    print(f"{'='*70}\n")
    
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. Load RPC articles
        print("📚 Loading RPC articles...")
        rpc_articles = load_rpc_articles(cur)
        print(f"   Loaded {len(rpc_articles)} RPC articles\n")
        
        # 2. Get cases to process - FILTER FOR TARGET YEAR
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
            ORDER BY id
        """
        
        params = [target_year]
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cur.execute(query, tuple(params))
        cases = cur.fetchall()
        
        print(f"🔍 Found {len(cases)} RPC cases to analyze\n")
        
        # 3. Process each case
        all_links = []
        stats = {
            'cases_processed': 0,
            'cases_with_links': 0,
            'total_links': 0,
            'multi_article_cases': 0,
            'multi_sentence_cases': 0
        }
        
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case['short_title']}")
            
            interpretations = analyze_case_rpc_links(case, rpc_articles)
            
            if interpretations:
                print(f"   ✅ Found {len(interpretations)} interpretation(s):")
                
                articles_mentioned = set()
                for interp in interpretations:
                    article = interp['article']
                    sent_idx = interp['sentence_index']
                    summary = interp['summary']
                    
                    articles_mentioned.add(article)
                    
                    sent_label = f"S{sent_idx}" if sent_idx >= 0 else "General"
                    print(f"      • Art. {article}, {sent_label}: {summary[:60]}...")
                    
                    all_links.append({
                        'case_id': case['id'],
                        'case_title': case['short_title'],
                        'article': article,
                        'sentence_index': sent_idx,
                        'summary': summary
                    })
                
                stats['cases_with_links'] += 1
                stats['total_links'] += len(interpretations)
                
                if len(articles_mentioned) > 1:
                    stats['multi_article_cases'] += 1
                if len(interpretations) > len(articles_mentioned):
                    stats['multi_sentence_cases'] += 1
            else:
                print(f"   ⊘ No RPC interpretations found")
            
            stats['cases_processed'] += 1
            print()
        
        # 4. Summary
        print(f"\n{'='*70}")
        print(f"PROCESSING SUMMARY")
        print(f"{'='*70}")
        print(f"Cases processed:           {stats['cases_processed']}")
        print(f"Cases with links:          {stats['cases_with_links']}")
        print(f"Total links created:       {stats['total_links']}")
        print(f"Multi-article cases:       {stats['multi_article_cases']}")
        print(f"Multi-sentence cases:      {stats['multi_sentence_cases']}")
        print(f"Avg links per case:        {stats['total_links'] / max(stats['cases_with_links'], 1):.1f}")
        
        # Article distribution
        article_distribution = {}
        for link in all_links:
            art = link['article']
            article_distribution[art] = article_distribution.get(art, 0) + 1
        
        print(f"\n📊 Top 10 Articles by Link Count:")
        for art, count in sorted(article_distribution.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   Article {art:>3}: {count:>4} links")
        
        # 5. Database commit (if not dry run)
        if not dry_run and all_links:
            print(f"\n💾 Writing {len(all_links)} links to database...")
            
            # Validate all links first
            print("   🔍 Validating links...")
            valid_links = []
            for link in all_links:
                # Check article exists
                if link['article'] not in rpc_articles:
                    print(f"   ⚠️  Skipping invalid article: {link['article']} (not in rpc_codal)")
                    continue
                
                # Validate sentence index is an integer
                try:
                    sent_idx = int(link['sentence_index'])
                except (ValueError, TypeError):
                    print(f"   ⚠️  Skipping link with invalid sentence_index: {link['sentence_index']}")
                    continue
                
                # Validate summary is not too long (max 4000 chars to be safe)
                summary = str(link['summary'])[:4000] if link['summary'] else "Verified interpretation"
                
                valid_links.append({
                    'case_id': link['case_id'],
                    'article': str(link['article']),
                    'sentence_index': sent_idx,
                    'summary': summary
                })
            
            print(f"   ✅ {len(valid_links)} valid links (skipped {len(all_links) - len(valid_links)})")
            
            # Delete existing RPC links for the TARGET YEAR only
            print(f"   🗑️  Deleting old links for year {target_year}...")
            cur.execute("""
                DELETE FROM codal_case_links 
                WHERE statute_id = 'RPC'
                AND case_id IN (
                    SELECT id FROM sc_decided_cases 
                    WHERE EXTRACT(YEAR FROM date) = %s
                )
            """, (target_year,))
            deleted = cur.rowcount
            print(f"   ✓ Deleted {deleted} old links for {target_year}")
            
            # Insert new links with error handling using savepoints
            inserted_count = 0
            failed_count = 0
            failed_links = []
            for i, link in enumerate(valid_links):
                try:
                    # Create a savepoint before each insert
                    cur.execute(f"SAVEPOINT insert_{i}")
                    
                    cur.execute("""
                        INSERT INTO codal_case_links (
                            case_id, statute_id, provision_id,
                            target_paragraph_index, specific_ruling, subject_area, is_resolved
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
               link['case_id'],
                        'RPC',
                        link['article'],
                        link['sentence_index'],
                        link['summary'],
                        'Criminal Law',
                        True
                    ))
                    
                    # Release savepoint if successful
                    cur.execute(f"RELEASE SAVEPOINT insert_{i}")
                    inserted_count += 1
                except Exception as e:
                    # Rollback to savepoint if failed
                    cur.execute(f"ROLLBACK TO SAVEPOINT insert_{i}")
                    failed_count += 1
                    failed_links.append({
                        'article': link['article'],
                        'case_id': link['case_id'],
                        'error': str(e)[:100]
                    })
                    if failed_count <= 5:  # Only print first 5 errors
                        print(f"   ⚠️  Failed to insert link for Article {link['article']}: {str(e)[:80]}")
            
            if failed_count > 5:
                print(f"   ... and {failed_count - 5} more failures")
            
            conn.commit()
            print(f"   ✅ Inserted {inserted_count} links ({failed_count} failed)")
        elif dry_run:
            print(f"\n🔒 DRY RUN - No database changes made")
            print(f"   Run with --commit to apply changes")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Universal RPC Case Linker')
    parser.add_argument('--limit', type=int, help='Limit number of cases to process')
    parser.add_argument('--year', type=int, default=2025, help='Year to process (default: 2025)')
    parser.add_argument('mode', nargs='?', choices=['dry-run', 'commit'], default='dry-run', help='Mode: dry-run or commit')
    
    args = parser.parse_args()
    
    dry_run = args.mode != 'commit'
    year = args.year
    
    print(f"\nMode: {'DRY RUN (review only)' if dry_run else 'COMMIT (will modify database)'}")
    print(f"Target Year: {year}")
    
    if not dry_run:
        confirm = input(f"\n⚠️  This will generate links for {year} cases. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    process_cases(limit=args.limit, dry_run=dry_run, target_year=year)
