import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def cleanup():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # 1. Inspect and Delete Subpoena
    print("--- Checking 'Subpoena' ---")
    cur.execute("SELECT id, full_text_md FROM sc_decided_cases WHERE document_type = 'Subpoena'")
    rows = cur.fetchall()
    for r in rows:
        print(f"Deleting Subpoena ID {r[0]}: {r[1][:50]}...")
        cur.execute("DELETE FROM sc_decided_cases WHERE id = %s", (r[0],))
    
    # 2. Normalize Uppercase Types
    normalization_map = {
        "RESOLUTION": "Resolution",
        "DECISION": "Decision",
        "AMENDED DECISION": "Amended Decision"
    }
    
    print("\n--- Normalizing Uppercase Types ---")
    for old, new in normalization_map.items():
        cur.execute("SELECT id, full_text_md FROM sc_decided_cases WHERE document_type = %s", (old,))
        rows = cur.fetchall()
        for r in rows:
            print(f"Normalizing ID {r[0]} ({old} -> {new}). Content: {r[1][:50]}...")
            cur.execute("UPDATE sc_decided_cases SET document_type = %s WHERE id = %s", (new, r[0]))

    # 3. Report Special Types
    print("\n--- Special Types (Preserving) ---")
    special_types = ["Judgment [Based on Compromise Agreement]", "Opinion on Defendant's Motion to Reconsider"]
    for st in special_types:
        cur.execute("SELECT id, full_text_md FROM sc_decided_cases WHERE document_type = %s", (st,))
        rows = cur.fetchall()
        for r in rows:
            print(f"Keeping ID {r[0]} ({st}). Content: {r[1][:50]}...")

    conn.commit()
    conn.close()
    print("\nDone.")

if __name__ == "__main__":
    cleanup()
