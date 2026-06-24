import os
import sys
import argparse
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from load_local_settings_env import load_api_local_settings_into_environ

load_api_local_settings_into_environ(SCRIPTS_DIR.parent)

DB_URL = (
    os.environ.get("DB_CONNECTION_STRING_AZURE")
    or os.environ.get("DB_CONNECTION_STRING")
)

def get_db_connection():
    if not DB_URL:
        raise ValueError("No database connection string found in environment.")
    return psycopg2.connect(DB_URL)

def main():
    parser = argparse.ArgumentParser(description="Prepare GR-only Grok-digested target cases for a specific year.")
    parser.add_argument("--year", type=int, required=True, help="Year of the cases to prepare (e.g. 2025)")
    args = parser.parse_args()
    
    year = args.year
    
    print(f"Connecting to database...")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Query for all Grok cases in the specified year NOT recently digested (before June 2026)
    # with the 'GR' case number variation.
    query = """
        SELECT id, case_number, short_title, date, ai_model, updated_at
        FROM sc_decided_cases
        WHERE position('grok' in lower(ai_model)) > 0
          AND EXTRACT(YEAR FROM date) = %s
          AND (updated_at < '2026-06-01' OR updated_at >= '2026-06-24 00:00:00')
          AND (
              position('g.r.' in lower(case_number)) > 0
              OR position('gr' in lower(case_number)) > 0
              OR position('g. r.' in lower(case_number)) > 0
          )
        ORDER BY id ASC
    """
    
    cur.execute(query, (year,))
    all_grok_cases = cur.fetchall()
    
    print(f"Year: {year}")
    print(f"Total Grok-digested cases matching 'GR' constraint: {len(all_grok_cases)}")
    
    # 2. Query for already redigested cases for that year (ai_model = gemini-3.5-flash) with the 'GR' constraint
    cur.execute("""
        SELECT id, case_number, short_title, date, ai_model, updated_at
        FROM sc_decided_cases
        WHERE ai_model = 'publishers/google/models/gemini-3.5-flash'
          AND EXTRACT(YEAR FROM date) = %s
          AND (
              position('g.r.' in lower(case_number)) > 0
              OR position('gr' in lower(case_number)) > 0
              OR position('g. r.' in lower(case_number)) > 0
          )
        ORDER BY id ASC
    """, (year,))
    already_redigested_cases = cur.fetchall()
    print(f"Already redigested cases matching 'GR' constraint: {len(already_redigested_cases)}")
    
    # The new target queue is the Grok cases that are not yet redigested
    already_redigested_ids = {r['id'] for r in already_redigested_cases}
    pending_cases = [r for r in all_grok_cases if r['id'] not in already_redigested_ids]
    
    print(f"Pending/Remaining cases left to redigest: {len(pending_cases)}")
    
    # Save the pending GR case IDs to target_grok_ids file (which the redigester script uses)
    pending_ids_str = ",".join(str(r['id']) for r in pending_cases)
    target_file = SCRIPTS_DIR / f"target_{year}_grok_ids.txt"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(pending_ids_str)
        
    print(f"Saved target IDs to: {target_file}")
    
    # Also save as the active "target_2025_grok_ids.txt" if year is 2025 for seamless compatibility
    if year == 2025:
        compat_file = SCRIPTS_DIR / "target_2025_grok_ids.txt"
        with open(compat_file, "w", encoding="utf-8") as f:
            f.write(pending_ids_str)
        print(f"Saved active compatibility target file: {compat_file}")
        
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
