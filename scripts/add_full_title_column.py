import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

HOST = "localhost"
USER = "postgres"
PASS = "b66398241bfe483ba5b20ca5356a87be"
DB = "bar_reviewer_local"

def add_full_title_column():
    conn = None
    try:
        conn = psycopg2.connect(host=HOST, user=USER, password=PASS, dbname=DB)
        conn.autocommit = True
        cur = conn.cursor()

        logging.info("Adding 'full_title' column...")
        cur.execute("""
            ALTER TABLE sc_decided_cases 
            ADD COLUMN IF NOT EXISTS full_title TEXT;
        """)
        
        logging.info("Column 'full_title' added successfully.")
        
        # Verify
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sc_decided_cases' AND column_name = 'full_title'
        """)
        exists = cur.fetchone()
        logging.info(f"Verification: Column exists = {bool(exists)}")

    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_full_title_column()
