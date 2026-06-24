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
    
    # Query all cases for gemini-2.0-flash
    query = """
        SELECT id, case_number, short_title, date, ai_model
        FROM sc_decided_cases
        WHERE ai_model = 'gemini-2.0-flash'
        ORDER BY date ASC, id ASC
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} cases:")
    for r in rows:
        print(repr(r))
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
