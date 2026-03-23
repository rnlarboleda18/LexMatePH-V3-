import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import date

# Configuration
CODE_SHORT_NAME = "RPC"
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def reapply_rpc_amendments():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("--- Starting Chronological Amendment Re-Application for RPC ---")

    # 1. Get Code ID
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (CODE_SHORT_NAME,))
    row = cur.fetchone()
    if not row:
        print(f"Code {CODE_SHORT_NAME} not found.")
        return
    code_id = row['code_id']

    # 2. Reset to Base Law (Act No. 3815)
    # We want to clear strict amendments but KEEP the base law? 
    # Or just wipe everything and re-ingest? 
    # Safer: Identify the *sequence* of amendments and re-run logic.
    # User said: "re apply all the amendments chronologically".
    
    # Let's fetch all versions for RPC
    cur.execute("""
        SELECT * FROM article_versions 
        WHERE code_id = %s 
        ORDER BY article_number, valid_from
    """, (code_id,))
    all_versions = cur.fetchall()
    
    # Strategy:
    # 1. Group by Article
    # 2. Sort versions by `valid_from` (ascending)
    # 3. Ensure `valid_to` of Version N matches `valid_from` of Version N+1
    # 4. If mismatched, UPDATE strict.
    
    print(f"Analyzing {len(all_versions)} article versions...")
    
    grouped = {}
    for v in all_versions:
        art = v['article_number']
        if art not in grouped: grouped[art] = []
        grouped[art].append(v)
        
    updated_count = 0
    
    for art, versions in grouped.items():
        # Sort by Date
        # Handle cases where valid_from might be same (shouldn't happen ideally)
        versions.sort(key=lambda x: x['valid_from'])
        
        for i in range(len(versions)):
            current = versions[i]
            
            # Logic for LAST item (Active)
            if i == len(versions) - 1:
                # Should have NULL valid_to
                if current['valid_to'] is not None:
                     print(f"Fixing Active Article {art} (Ver {current['version_id']}): Setting valid_to = NULL")
                     cur.execute("UPDATE article_versions SET valid_to = NULL WHERE version_id = %s", (current['version_id'],))
                     updated_count += 1
                continue
                
            # Logic for HISTORICAL items
            next_ver = versions[i+1]
            
            # The current version should expire exactly when the next one starts
            correct_end_date = next_ver['valid_from']
            
            if current['valid_to'] != correct_end_date:
                print(f"Fixing History Article {art}: Ver {current['version_id']} ends {current['valid_to']}, should end {correct_end_date}")
                cur.execute("UPDATE article_versions SET valid_to = %s WHERE version_id = %s", (correct_end_date, current['version_id']))
                updated_count += 1

    conn.commit()
    print(f"Re-application Complete. Fixed {updated_count} date discontinuities.")
    conn.close()

if __name__ == "__main__":
    reapply_rpc_amendments()
