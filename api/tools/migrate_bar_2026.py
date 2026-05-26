"""
Migration: Bar 2026 schema updates.
  1. Add key_statutes JSONB column
  2. Drop old chk_confidence constraint (had 'search-grounded', missing 'mixed')
  3. Remap existing 'search-grounded' rows to 'mixed'
  4. Re-add constraint with correct values
Run from api/ directory: python tools/migrate_bar_2026.py
"""
import os
import json
import psycopg2


def load_settings():
    try:
        with open("local.settings.json") as f:
            data = json.load(f)
            vals = data.get("Values", {})
            db = (vals.get("DB_CONNECTION_STRING") or "").strip()
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = v
            if db and "DB_CONNECTION_STRING" not in os.environ:
                os.environ["DB_CONNECTION_STRING"] = db
    except Exception:
        pass


STEPS = [
    ("Add key_statutes column",
     "ALTER TABLE bar_reviewer_topics ADD COLUMN IF NOT EXISTS key_statutes JSONB"),
    ("Drop old confidence constraint",
     "ALTER TABLE bar_reviewer_topics DROP CONSTRAINT IF EXISTS chk_confidence"),
    ("Remap search-grounded to mixed",
     "UPDATE bar_reviewer_topics SET confidence = 'mixed' WHERE confidence = 'search-grounded'"),
    ("Add updated confidence constraint",
     "ALTER TABLE bar_reviewer_topics ADD CONSTRAINT chk_confidence "
     "CHECK (confidence IN ('db-sourced', 'mixed', 'ai-synthesized'))"),
]

if __name__ == "__main__":
    load_settings()
    conn_str = os.environ.get("DB_CONNECTION_STRING", "")
    if not conn_str:
        print("ERROR: DB_CONNECTION_STRING not set.")
        exit(1)

    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()

    for desc, sql in STEPS:
        print(f"  >> {desc}...")
        cur.execute(sql)
        print(f"     OK")

    cur.close()
    conn.close()
    print("\nMigration complete.")
