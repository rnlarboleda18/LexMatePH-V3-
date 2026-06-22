"""
Create sc_case_digest_history table and backfill existing entries.
"""
import json
import os
import sys
import psycopg2

API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(API_ROOT, "local.settings.json")

sql = """
CREATE TABLE IF NOT EXISTS sc_case_digest_history (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES sc_decided_cases(id) ON DELETE CASCADE,
    ai_model VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    fields_changed TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sc_case_digest_history_case_id ON sc_case_digest_history(case_id);

-- Initial backfill for existing cases that have an ai_model
INSERT INTO sc_case_digest_history (case_id, ai_model, action, fields_changed, created_at)
SELECT 
    id, 
    ai_model, 
    'digest', 
    ARRAY['digest_facts', 'digest_issues', 'digest_ruling', 'digest_ratio', 'main_doctrine'], 
    COALESCE(updated_at, NOW())
FROM sc_decided_cases
WHERE ai_model IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM sc_case_digest_history h WHERE h.case_id = sc_decided_cases.id
  );
"""

def main() -> None:
    if not os.path.isfile(SETTINGS):
        print(f"Missing local.settings.json at {SETTINGS}", file=sys.stderr)
        sys.exit(1)
    with open(SETTINGS, encoding="utf-8") as f:
        vals = json.load(f).get("Values") or {}
    conn_str = (vals.get("DB_CONNECTION_STRING") or "").strip()
    if not conn_str:
        print("DB_CONNECTION_STRING empty in local.settings.json", file=sys.stderr)
        sys.exit(1)
    
    print("Connecting to database and applying migration...")
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(sql)
        print("Migration applied successfully!")
    except Exception as e:
        print(f"Error executing migration: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
