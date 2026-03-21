
import os
import json
import psycopg2

def get_db_connection():
    try:
        settings_path = 'local.settings.json'
        if not os.path.exists(settings_path):
             settings_path = '../local.settings.json'
        if not os.path.exists(settings_path):
             settings_path = 'c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/local.settings.json'
             
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
                conn_str = settings['Values']['DB_CONNECTION_STRING']
                return conn_str
    except Exception:
        pass
    
    return "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@127.0.0.1:5432/bar_reviewer_local"

def clear_for_rerun():
    db_conn_string = get_db_connection()
    conn_string = db_conn_string.replace("localhost", "127.0.0.1")

    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()

        # Delete versions for RA 47 and RA 1084
        # We also need to "re-open" the previous versions (set valid_to = NULL) to restore state?
        # Actually, process_amendment.py handles closing old ones. 
        # But if we just delete the new ones, the old ones will still be closed (valid_to is set).
        # We should properly revert: delete new versions AND set valid_to=NULL on the ones that were closed by these amendments.
        
        amendments = ['Republic Act No. 47', 'Republic Act No. 1084']
        
        for amd in amendments:
            print(f"Rolling back {amd}...")
            
            # 1. Find the date this amendment was applied (valid_from of new versions)
            cursor.execute("SELECT MIN(valid_from) FROM article_versions WHERE amendment_id = %s", (amd,))
            date_row = cursor.fetchone()
            if not date_row or not date_row[0]:
                print(f"  No versions found for {amd}")
                continue
                
            amd_date = date_row[0]
            
            # 2. Delete the new versions
            cursor.execute("DELETE FROM article_versions WHERE amendment_id = %s", (amd,))
            deleted = cursor.rowcount
            print(f"  Deleted {deleted} new versions.")
            
            # 3. Re-open the old versions (where valid_to = amd_date)
            # This is a bit heuristic but should work if dates match.
            # Ideally we'd link by ID but we don't have straightforward parent linkage yet except via date overlap
            cursor.execute("""
                UPDATE article_versions 
                SET valid_to = NULL 
                WHERE valid_to = %s
            """, (amd_date,))
            reopened = cursor.rowcount
            print(f"  Re-opened {reopened} previous versions.")
            
        conn.commit()
        print("Rollback complete.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        if conn:
             conn.close()

if __name__ == "__main__":
    clear_for_rerun()
