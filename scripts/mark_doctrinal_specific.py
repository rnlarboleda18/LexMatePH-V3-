import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

def mark_doctrinal():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    target_ids = [36129, 41142]
    
    try:
        cur.execute("UPDATE sc_decided_cases SET is_doctrinal = TRUE WHERE id IN %s", (tuple(target_ids),))
        conn.commit()
        print(f"Successfully marked IDs {target_ids} as doctrinal.")
    except Exception as e:
        conn.rollback()
        print(f"Error updating cases: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    mark_doctrinal()
