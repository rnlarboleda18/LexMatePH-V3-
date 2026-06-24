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
    
    # Query the 10 cases in 2026 for gemini-3-flash-preview
    query = """
        SELECT id, case_number, short_title, date, ai_model
        FROM sc_decided_cases
        WHERE EXTRACT(YEAR FROM date) = 2026
          AND ai_model = 'gemini-3-flash-preview'
        ORDER BY date ASC, id ASC
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} cases:")
    for r in rows:
        print(r)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
