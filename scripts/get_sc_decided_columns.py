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
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'sc_decided_cases'")
    columns = cur.fetchall()
    print("sc_decided_cases columns:")
    for col, dtype in columns:
        print(f"  - {col}: {dtype}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
