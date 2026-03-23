import os
import psycopg2
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(message)s')

HOST = "localhost"
USER = "postgres"
PASS = "b66398241bfe483ba5b20ca5356a87be"
DB = "lexmateph-ea-db"
MD_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md"

def ingest_files():
    conn = None
    try:
        conn = psycopg2.connect(host=HOST, user=USER, password=PASS, dbname=DB)
        conn.autocommit = True
        cur = conn.cursor()

        files = []
        for root, dirs, filenames in os.walk(MD_DIR):
            for f in filenames:
                if f.casefold().endswith('.md'):
                    files.append(os.path.join(root, f))
        
        logging.info(f"Found {len(files)} Markdown files recursively in {MD_DIR}")
        
        if not files:
            logging.warning("No files found. Check directory path.")
            return

        count = 0
        for filepath in tqdm(files):
            try:
                filename = os.path.basename(filepath)
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Insert: ID is auto-filled (SERIAL)
                # We also save the filename in 'scrape_source' to track origin
                cur.execute("""
                    INSERT INTO sc_decided_cases (full_text_md, scrape_source, created_at, updated_at) 
                    VALUES (%s, %s, NOW(), NOW())
                """, (content, filename))
                count += 1
            except Exception as e:
                logging.error(f"Failed to ingest {filename}: {e}")

        logging.info(f"Successfully ingested {count} records.")

        # Verify count
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases")
        total = cur.fetchone()[0]
        logging.info(f"Total rows in database: {total}")

    except Exception as e:
        logging.error(f"Database Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    ingest_files()
