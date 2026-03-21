import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    target_id = "df68434a-a708-4e8c-a1ba-fc1bf3dfb609" # Section 9 example
    print(f"Inspecting ID: {target_id} in Cloud DB...")
    cur.execute("SELECT * FROM roc_codal WHERE id = %s", (target_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        print("Row not found.")
        return

    print("\n--- ROW DATA ---")
    for k, v in row.items():
        print(f"{k}: {v!r}")

if __name__ == "__main__":
    main()
