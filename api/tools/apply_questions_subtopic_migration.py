"""
Apply sub_topic column to public.questions using ONLY api/local.settings.json.

Why: run_migration.py skips loading DB_CONNECTION_STRING from the file when the
variable is already set in the environment, so migrations can target the wrong DB.
"""
import json
import os
import sys

import psycopg2

API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(API_ROOT, "local.settings.json")

sql = """
ALTER TABLE questions
ADD COLUMN IF NOT EXISTS sub_topic VARCHAR(100) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_questions_sub_topic
ON questions(sub_topic);

CREATE INDEX IF NOT EXISTS idx_questions_sub_topic_year
ON questions(sub_topic, year DESC);
"""


def main() -> None:
    if not os.path.isfile(SETTINGS):
        print("Missing local.settings.json", file=sys.stderr)
        sys.exit(1)
    with open(SETTINGS, encoding="utf-8") as f:
        vals = json.load(f).get("Values") or {}
    conn_str = (vals.get("DB_CONNECTION_STRING") or "").strip()
    if not conn_str:
        print("DB_CONNECTION_STRING empty in local.settings.json", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.close()
    print("OK: migration applied against DB from local.settings.json only.")


if __name__ == "__main__":
    main()
