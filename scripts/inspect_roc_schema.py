import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Connecting to Cloud DB...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("Fetching column types for 'roc_codal'...")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'roc_codal'
    """)
    rows = cur.fetchall()
    
    print("\n--- Columns ---")
    for r in rows:
         print(f"  {r['column_name']} -> {r['data_type']}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
