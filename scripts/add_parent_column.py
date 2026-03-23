import psycopg2

HOST = "localhost"
USER = "postgres"
PASS = "b66398241bfe483ba5b20ca5356a87be"
DB = "lexmateph-ea-db"

def add_parent_column():
    try:
        conn = psycopg2.connect(host=HOST, user=USER, password=PASS, dbname=DB)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Adding 'parent_id' column...")
        cur.execute("""
            ALTER TABLE sc_decided_cases 
            ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES sc_decided_cases(id);
        """)
        
        # Create index for performance
        print("Creating index on 'parent_id'...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_id ON sc_decided_cases(parent_id);
        """)

        print("Done.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_parent_column()
