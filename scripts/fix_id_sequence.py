import psycopg2

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def fix_id_sequence():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Checking max ID...")
        cur.execute("SELECT MAX(id) FROM sc_decided_cases")
        max_id = cur.fetchone()[0] or 0
        print(f"Current Max ID: {max_id}")
        
        print("Creating sequence if not exists...")
        cur.execute("CREATE SEQUENCE IF NOT EXISTS sc_decided_cases_id_seq")
        
        print(f"Setting sequence start to {max_id + 1}...")
        cur.execute(f"SELECT setval('sc_decided_cases_id_seq', {max_id + 1}, false)")
        
        print("Altering table to use sequence...")
        cur.execute("ALTER TABLE sc_decided_cases ALTER COLUMN id SET DEFAULT nextval('sc_decided_cases_id_seq')")
        
        print("Success! ID column now uses sequence.")
        
        # Verify
        cur.execute("""
            SELECT column_name, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'sc_decided_cases' AND column_name = 'id'
        """)
        print(f"Verification: {cur.fetchone()}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_id_sequence()
