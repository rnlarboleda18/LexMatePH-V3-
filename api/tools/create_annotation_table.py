"""
Migration: Create bar_topic_annotations table for S Pen / page annotations.
Run from the api/ directory: python tools/create_annotation_table.py
"""
import json
import os
import psycopg2


def load_settings():
    try:
        with open("local.settings.json") as f:
            data = json.load(f)
            vals = data.get("Values", {})
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


load_settings()

SQL = """
CREATE TABLE IF NOT EXISTS bar_topic_annotations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id    UUID NOT NULL REFERENCES bar_reviewer_topics(id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    strokes     JSONB NOT NULL DEFAULT '[]',
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (topic_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_annotations_topic_user
    ON bar_topic_annotations(topic_id, user_id);
"""

conn_str = os.environ.get("DB_CONNECTION_STRING", "")
if not conn_str:
    raise SystemExit("ERROR: DB_CONNECTION_STRING not set. Run from api/ directory with local.settings.json present.")

conn = psycopg2.connect(conn_str)
try:
    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    print("OK: bar_topic_annotations table created (or already exists)")
finally:
    conn.close()
