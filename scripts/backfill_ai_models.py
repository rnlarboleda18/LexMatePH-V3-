import psycopg2
import os
import re

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
REPORT_FILE = 'gemini_2_digests_report.txt'

# Hardcoded from launch_long_cases_worker.ps1
LONG_CASE_IDS = [20140,51520,44814,63787,3615,8877,49448,32678,42813,59123,33992,17998,45141,5642,24065,45057,33441,3245,32256,63811]

def get_elite_ids():
    if not os.path.exists(REPORT_FILE):
        return []
    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    ids = re.findall(r'ID: (\d+)', content)
    return sorted(list(set([int(x) for x in ids])))

def main():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    try:
        # 1. Update Long Cases (Gemini 3 Pro)
        print("Backfilling Long Cases (Gemini 3 Pro)...")
        if LONG_CASE_IDS:
            placeholders = ','.join(['%s'] * len(LONG_CASE_IDS))
            query = f"""
                UPDATE sc_decided_cases 
                SET ai_model = 'gemini-3-pro-preview' 
                WHERE id IN ({placeholders}) 
                AND digest_significance IS NOT NULL -- Only if actually digested
            """
            cur.execute(query, tuple(LONG_CASE_IDS))
            print(f"Updated {cur.rowcount} long cases.")
        
        # 2. Update Elite Fleet Cases (Gemini 2.5 Pro)
        print("Backfilling Elite Fleet (Gemini 2.5 Pro)...")
        elite_ids = get_elite_ids()
        # Filter out Long Case IDs from Elite IDs to avoid overwriting (if any overlap)
        elite_ids = [x for x in elite_ids if x not in LONG_CASE_IDS]
        
        if elite_ids:
            placeholders = ','.join(['%s'] * len(elite_ids))
            query = f"""
                UPDATE sc_decided_cases 
                SET ai_model = 'gemini-2.5-pro' 
                WHERE id IN ({placeholders}) 
                AND digest_significance IS NOT NULL -- Only if actually digested
                AND (ai_model IS NULL OR ai_model != 'gemini-3-pro-preview')
            """
            cur.execute(query, tuple(elite_ids))
            print(f"Updated {cur.rowcount} elite cases.")
            
        # 3. Update Historical Fleet (Gemini 2.5 Flash)
        # Any digested case in 1901-1945 that hasn't been set yet
        print("Backfilling Historical Fleet (Gemini 2.5 Flash)...")
        query = """
            UPDATE sc_decided_cases 
            SET ai_model = 'gemini-2.5-flash' 
            WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1945
            AND digest_significance IS NOT NULL
            AND ai_model IS NULL
        """
        cur.execute(query)
        print(f"Updated {cur.rowcount} historical cases.")

        conn.commit()
        print("Backfill Complete.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
