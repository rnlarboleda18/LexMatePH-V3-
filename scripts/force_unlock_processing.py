import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def force_unlock():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print("Checking for cases stuck in 'PROCESSING'...", flush=True)
    
    # Check count first
    cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_significance = 'PROCESSING'")
    count = cur.fetchone()[0]
    
    if count == 0:
        print("No locked cases found.")
        return

    print(f"Found {count} locked cases. Unlocking...", flush=True)
    
    # Reset to NULL (or previous state? usually just NULL/Unknown to be picked up again)
    # The script uses 'digest_significance' as the lock.
    cur.execute("UPDATE sc_decided_cases SET digest_significance = NULL WHERE digest_significance = 'PROCESSING'")
    conn.commit()
    
    print("Successfully unlocked all locks.", flush=True)
    conn.close()

if __name__ == "__main__":
    force_unlock()
