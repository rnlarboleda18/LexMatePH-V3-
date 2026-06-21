import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    # Attempt to load connection string from local.settings.json or use env
    conn_str = os.environ.get("DB_CONNECTION_STRING")
    if not conn_str:
        try:
            # Look for local.settings.json in current directory or parent directory
            settings_paths = ['local.settings.json', '../local.settings.json', '../../local.settings.json']
            for path in settings_paths:
                if os.path.exists(path):
                    with open(path) as f:
                        settings = json.load(f)
                        conn_str = settings['Values'].get('DB_CONNECTION_STRING')
                        if conn_str:
                            break
        except Exception:
            pass
            
    if not conn_str:
        # Fallback to local DB default
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
        
    return psycopg2.connect(conn_str)

def purge_empty_cases():
    print("Connecting to the database...")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. Identify all cases where short_title is NULL or empty
        print("Scanning for empty/incomplete cases in sc_decided_cases...")
        cur.execute(
            "SELECT id, sc_url, date, full_title FROM sc_decided_cases WHERE short_title IS NULL OR short_title = ''"
        )
        empty_cases = cur.fetchall()
        
        if not empty_cases:
            print("\nPerfect! No empty/incomplete cases found in the database. Nothing to purge.")
            return
            
        print(f"\nFound {len(empty_cases)} empty/incomplete cases to purge:")
        for idx, case in enumerate(empty_cases, 1):
            title = case['full_title'][:60] if case['full_title'] else "(No Title)"
            print(f"  {idx}. ID: {case['id']} | Date: {case['date']} | URL: {case['sc_url']} | Title: {title}...")
            
        case_ids = [case['id'] for case in empty_cases]
        
        print("\nStarting purge of empty cases...")
        
        # 2. Delete/Nullify associated child records first to satisfy FK constraints
        print("  - Deleting associated codal links from codal_case_links...")
        cur.execute("DELETE FROM codal_case_links WHERE case_id = ANY(%s)", (case_ids,))
        
        print("  - Deleting associated jurisprudence links from jurisprudence_links...")
        cur.execute("DELETE FROM jurisprudence_links WHERE case_id = ANY(%s)", (case_ids,))
        
        print("  - Nullifying parent_id self-references in sc_decided_cases...")
        cur.execute("UPDATE sc_decided_cases SET parent_id = NULL WHERE parent_id = ANY(%s)", (case_ids,))
        
        # 3. Finally, delete the cases themselves
        print("  - Deleting empty cases from sc_decided_cases...")
        cur.execute("DELETE FROM sc_decided_cases WHERE id = ANY(%s)", (case_ids,))
        
        conn.commit()
        print(f"\nSuccess! Successfully purged {len(empty_cases)} empty cases from the database.")
        
    except Exception as e:
        conn.rollback()
        print(f"\nError: Failed to purge empty cases: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    purge_empty_cases()
