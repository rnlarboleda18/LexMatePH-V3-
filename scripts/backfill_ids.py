import psycopg2

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def backfill_ids():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        print("Backfilling NULL IDs...")
        cur.execute("UPDATE sc_decided_cases SET id = nextval('sc_decided_cases_id_seq') WHERE id IS NULL")
        updated_rows = cur.rowcount
        conn.commit()
        print(f"Updated {updated_rows} rows.")
        
        # Verify
        cur.execute("SELECT MIN(id), MAX(id) FROM sc_decided_cases")
        stats = cur.fetchone()
        print(f"New ID Range: Min={stats[0]}, Max={stats[1]}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    backfill_ids()
