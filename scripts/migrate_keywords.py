
import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def migrate_keywords():
    print("Starting Keywords Migration to JSONB...")
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Execute Alter Table
        # to_jsonb(keywords) handles text[] -> jsonb conversion nicely (['a','b'] -> ["a", "b"])
        cur.execute("ALTER TABLE sc_decided_cases ALTER COLUMN keywords TYPE JSONB USING to_jsonb(keywords);")
        
        conn.commit()
        print("Migration Successful!")
        conn.close()
    except Exception as e:
        print(f"Migration Failed: {e}")

if __name__ == "__main__":
    migrate_keywords()
