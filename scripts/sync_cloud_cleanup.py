import psycopg2

# Configuration from ingest_supreme_to_postgres.py
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

TABLES_TO_REMOVE = [
    "bar_exam_cycles",
    "batch_jobs",
    "exam_schedules",
    "jurisprudence_links",
    "user_attempts"
]

def cleanup_cloud():
    print(f"Connecting to Cloud DB: bar-reviewer-app-db...")
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        print("Starting Cloud DB cleanup (Removing 5 unused tables)...")
        
        for table in TABLES_TO_REMOVE:
            try:
                print(f"  Dropping table: {table}...", end=" ", flush=True)
                cur.execute(f"DROP TABLE IF EXISTS \"{table}\" CASCADE")
                print("OK")
            except Exception as e:
                print(f"FAILED: {e}")
                conn.rollback()
                continue
                
        conn.commit()
        print("\nCloud cleanup complete. Verifying...")
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        remaining = [row[0] for row in cur.fetchall()]
        
        for table in TABLES_TO_REMOVE:
            if table in remaining:
                print(f"  WARNING: {table} still exists in Cloud DB!")
            else:
                print(f"  Confirmed: {table} removed from Cloud DB.")
                
        conn.close()
    except Exception as e:
        print(f"Critical connection error: {e}")

if __name__ == "__main__":
    cleanup_cloud()
