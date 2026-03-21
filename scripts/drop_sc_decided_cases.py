import psycopg2

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def drop_table():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Dropping table sc_decided_cases...")
        cur.execute("DROP TABLE IF EXISTS sc_decided_cases")
        
        print("Table dropped successfully.")
        
        # Verify
        cur.execute("SELECT to_regclass('public.sc_decided_cases')")
        if cur.fetchone()[0] is None:
            print("Verification: Table no longer exists.")
        else:
            print("Verification FAILED: Table still exists.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    drop_table()
