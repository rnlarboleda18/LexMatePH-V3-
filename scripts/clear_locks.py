import os
import psycopg
import json

def clear_locks():
    conn_str = os.environ.get("DB_CONNECTION_STRING")
    if not conn_str:
        try:
            with open("api/local.settings.json", "r") as f:
                settings = json.load(f)
                conn_str = settings["Values"]["DB_CONNECTION_STRING"]
        except:
            pass
            
    if not conn_str:
        print("Error: Could not find connection string.")
        return

    with psycopg.connect(conn_str, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE sc_decisions SET digest_significance = NULL WHERE digest_significance = 'PROCESSING'")
            print(f"Cleared {cur.rowcount} stale locks.")

if __name__ == "__main__":
    clear_locks()
