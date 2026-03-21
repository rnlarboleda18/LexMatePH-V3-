import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    try:
        print("Creating batch_jobs table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id SERIAL PRIMARY KEY,
                google_batch_id VARCHAR(255) UNIQUE NOT NULL,
                status VARCHAR(50) DEFAULT 'processing',
                local_batch_filename VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                metadata JSONB -- Flexible field for extra info (e.g. model used, date range)
            );
        """)
        conn.commit()
        print("Success: batch_jobs table ready.")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
