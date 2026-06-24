import os
import psycopg2
import sys
from pathlib import Path

# Setup paths
_SCRIPTS = Path(__file__).resolve().parent
_WORKSPACE = _SCRIPTS.parent
sys.path.append(str(_WORKSPACE))
sys.path.append(str(_WORKSPACE / "api"))

import load_local_settings_env

def get_db_connection():
    db_url = os.environ.get("DB_CONNECTION_STRING_AZURE") or os.environ.get("DB_CONNECTION_STRING")
    if not db_url:
        raise ValueError("No database connection string found in environment.")
    return psycopg2.connect(db_url)

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Distinct AI models containing 'flash' or 'gemini'
    cur.execute("SELECT DISTINCT ai_model FROM sc_decided_cases WHERE ai_model IS NOT NULL")
    models = [row[0] for row in cur.fetchall()]
    print("Distinct AI models in DB:")
    for model in sorted(models):
        print(f"  - {model}")
        
    print("\n" + "="*50 + "\n")
    
    # 2. Count for publishers/google/models/gemini-3.5-flash overall
    cur.execute("""
        SELECT COUNT(*) 
        FROM sc_decided_cases 
        WHERE ai_model = 'publishers/google/models/gemini-3.5-flash'
    """)
    total_flash = cur.fetchone()[0]
    print(f"Total digested by Gemini 3.5 Flash: {total_flash}")
    
    # 3. Count for publishers/google/models/gemini-3.5-flash updated within last 7 days
    cur.execute("""
        SELECT COUNT(*) 
        FROM sc_decided_cases 
        WHERE ai_model = 'publishers/google/models/gemini-3.5-flash' 
          AND updated_at >= NOW() - INTERVAL '7 days'
    """)
    recent_flash = cur.fetchone()[0]
    print(f"Gemini 3.5 Flash digested recently (within 7 days): {recent_flash}")
    
    # 4. Count for publishers/google/models/gemini-3.5-flash updated NOT within last 7 days (or updated_at is null)
    cur.execute("""
        SELECT COUNT(*) 
        FROM sc_decided_cases 
        WHERE ai_model = 'publishers/google/models/gemini-3.5-flash' 
          AND (updated_at < NOW() - INTERVAL '7 days' OR updated_at IS NULL)
    """)
    old_flash = cur.fetchone()[0]
    print(f"Gemini 3.5 Flash digested NOT recently (over 7 days ago or NULL): {old_flash}")
    
    # Let's also check if there are other Gemini 3.5 models
    for model in sorted(models):
        if 'gemini' in model.lower() and model != 'publishers/google/models/gemini-3.5-flash':
            cur.execute("""
                SELECT COUNT(*) FROM sc_decided_cases WHERE ai_model = %s
            """, (model,))
            cnt = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*) FROM sc_decided_cases WHERE ai_model = %s AND (updated_at < NOW() - INTERVAL '7 days' OR updated_at IS NULL)
            """, (model,))
            old_cnt = cur.fetchone()[0]
            print(f"Model '{model}': Total = {cnt}, Not recently = {old_cnt}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
