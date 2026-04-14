import os
import psycopg

conn_string = os.environ.get("DB_CONNECTION_STRING", "postgresql://postgres:postgres@localhost:5432/postgres")

schema_changes = """
-- First try to create the tables if they don't exist at all
CREATE TABLE IF NOT EXISTS playlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Legacy installs: playlists.user_id was UUID; Clerk `sub` is a string (e.g. user_2abc…).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'playlists'
          AND column_name = 'user_id'
          AND udt_name = 'uuid'
    ) THEN
        ALTER TABLE playlists ALTER COLUMN user_id TYPE VARCHAR(255) USING user_id::text;
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'playlists.user_id UUID→VARCHAR migration skipped: %', SQLERRM;
END $$;

CREATE TABLE IF NOT EXISTS playlist_items (
    id SERIAL PRIMARY KEY,
    playlist_id UUID REFERENCES playlists(id) ON DELETE CASCADE,
    content_id TEXT NOT NULL, 
    content_type TEXT CHECK (content_type IN ('codal', 'case')),
    code_id TEXT,
    title TEXT,
    subtitle TEXT,
    sort_order INT NOT NULL,
    UNIQUE(playlist_id, sort_order)
);

CREATE TABLE IF NOT EXISTS user_playback_state (
    user_id TEXT PRIMARY KEY,
    playlist_id UUID REFERENCES playlists(id) ON DELETE SET NULL,
    current_track_id TEXT,
    "current_time" FLOAT DEFAULT 0,
    playback_rate FLOAT DEFAULT 1.0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- If they already exist from a previous version, alter them safely:
DO $$ 
BEGIN 
    -- Change content_id from UUID to TEXT
    BEGIN
        ALTER TABLE playlist_items ALTER COLUMN content_id TYPE TEXT USING content_id::text;
    EXCEPTION WHEN undefined_table THEN
        -- Ignore if table doesn't exist yet
    END;

    -- Add missing metadata columns
    BEGIN
        ALTER TABLE playlist_items ADD COLUMN code_id TEXT;
    EXCEPTION WHEN duplicate_column THEN END;

    BEGIN
        ALTER TABLE playlist_items ADD COLUMN title TEXT;
    EXCEPTION WHEN duplicate_column THEN END;
    
    BEGIN
        ALTER TABLE playlist_items ADD COLUMN subtitle TEXT;
    EXCEPTION WHEN duplicate_column THEN END;
END $$;
"""

def migrate():
    print("Starting Playlist Migration...")
    try:
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute(schema_changes)
                conn.commit()
                print("Migration applied successfully!")
                
                # Verify columns
                cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'playlist_items';")
                rows = cur.fetchall()
                print("Current playlist_items Schema:")
                for r in rows:
                    print(f" - {r[0]}: {r[1]}")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
