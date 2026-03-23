import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

HOST = "localhost"
USER = "postgres"
PASS = "b66398241bfe483ba5b20ca5356a87be"
DB = "lexmateph-ea-db"

def clear_data():
    conn = None
    try:
        conn = psycopg2.connect(host=HOST, user=USER, password=PASS, dbname=DB)
        conn.autocommit = True
        cur = conn.cursor()

        logging.info("!!! WARNING: DELETING ALL DATA IN sc_decided_cases !!!")
        
        # TRUNCATE is faster than DELETE and resets sequences
        # CASCADE is needed if other tables ref it (or for parent_id)
        cur.execute("TRUNCATE TABLE sc_decided_cases CASCADE;")
        
        logging.info("Table truncated successfully.")
        
        # Verify
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases")
        count = cur.fetchone()[0]
        logging.info(f"Remaining records: {count}")

    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    clear_data()
