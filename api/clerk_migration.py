import os
import psycopg
import logging

import json

# Try to load conn string from local.settings.json
conn_string = None
try:
    with open('local.settings.json') as f:
        data = json.load(f)
        conn_string = data.get('Values', {}).get('DB_CONNECTION_STRING')
except:
    pass

if not conn_string:
    conn_string = os.environ.get("DB_CONNECTION_STRING", "postgresql://postgres:postgres@localhost:5432/postgres")

migration_sql = """
-- 1. Create Users table for Clerk Sync
CREATE TABLE IF NOT EXISTS users (
    clerk_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Update Playlists table
DO $$ 
BEGIN 
    -- Alter user_id from UUID to VARCHAR(255)
    ALTER TABLE playlists ALTER COLUMN user_id TYPE VARCHAR(255) USING user_id::text;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Could not alter playlists.user_id - might already be VARCHAR or table missing';
END $$;

-- 3. Update scores table
DO $$ 
BEGIN 
    -- Alter user_id to VARCHAR(255)
    -- We use DO block to be safe if table is missing
    BEGIN
        ALTER TABLE user_mock_scores ALTER COLUMN user_id TYPE VARCHAR(255) USING user_id::text;
    EXCEPTION WHEN undefined_table THEN
        RAISE NOTICE 'Table user_mock_scores not found, skipping.';
    END;
END $$;
"""

def migrate():
    print("Starting Clerk Database Migration...")
    try:
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
                conn.commit()
                print("Clerk Migration applied successfully!")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
