import psycopg2
import json
import os

def release_locks():
    try:
        # Load connection string
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']

        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()

        # Check for locked cases
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE ai_model = 'PROCESSING'")
        count = cur.fetchone()[0]
        
        if count > 0:
            print(f"Found {count} locked cases (PROCESSING). Releasing...")
            cur.execute("UPDATE sc_decided_cases SET ai_model = NULL WHERE ai_model = 'PROCESSING'")
            conn.commit()
            print("Locks released.")
        else:
            print("No locked cases found (no 'PROCESSING' status).")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    release_locks()
