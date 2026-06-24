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
    
    cur.execute("""
        SELECT id, updated_at, ai_model
        FROM sc_decided_cases 
        WHERE ai_model IN ('publishers/google/models/gemini-3.5-flash', 'gemini-3.5-flash') 
          AND (updated_at < NOW() - INTERVAL '7 days' OR updated_at IS NULL)
    """)
    rows = cur.fetchall()
    print(f"Found {len(rows)} matching cases:")
    for row in rows:
        print(f"ID: {row[0]}, Updated At: {row[1]}, Model: {row[2]}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
