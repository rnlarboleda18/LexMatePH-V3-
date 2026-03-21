import psycopg2
import logging
import os

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

logging.basicConfig(level=logging.INFO)

def run_migration():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        logging.info("Checking if 'separate_opinions' column exists...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='supreme_decisions' AND column_name='separate_opinions';
        """)
        if cur.fetchone():
            logging.info("Column 'separate_opinions' already exists.")
        else:
            logging.info("Adding 'separate_opinions' column...")
            cur.execute("ALTER TABLE supreme_decisions ADD COLUMN separate_opinions JSONB;")
            conn.commit()
            logging.info("Column added successfully.")
            
        conn.close()
    except Exception as e:
        logging.error(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
