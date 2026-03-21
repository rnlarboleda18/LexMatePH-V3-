
import psycopg2
import os

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def fix_mojibake():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Inspect
    cid = 43290
    cur.execute("SELECT short_title FROM sc_decided_cases WHERE id = %s", (cid,))
    title = cur.fetchone()[0]
    print(f"Current Title [{cid}]: {title}")
    
    # Fix
    if "â€™" in title or "â€" in title:
        new_title = title.replace("â€™", "'").replace("â€", "")
        # Remove any other potential garbage if found, usually 'â€™' maps to apostrophe in CP1252->UTF8
        print(f"Fixing to: {new_title}")
        cur.execute("UPDATE sc_decided_cases SET short_title = %s WHERE id = %s", (new_title, cid))
        conn.commit()
        print("Update Executed.")
    else:
        print("No match found for replacement.")

    conn.close()

if __name__ == "__main__":
    fix_mojibake()
