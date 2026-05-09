"""Create bp68_processed_cases tracking table and backfill from existing links."""
import json, psycopg2
from pathlib import Path

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor()

# Create tracking table
cur.execute("""
    CREATE TABLE IF NOT EXISTS bp68_processed_cases (
        case_id INTEGER PRIMARY KEY,
        processed_at TIMESTAMPTZ DEFAULT NOW()
    )
""")

# Backfill from cases that already have BP_68 links
cur.execute("""
    INSERT INTO bp68_processed_cases (case_id)
    SELECT DISTINCT case_id FROM codal_case_links WHERE decided_under = 'BP_68'
    ON CONFLICT (case_id) DO NOTHING
""")
backfilled = cur.rowcount
conn.commit()

cur.execute("SELECT COUNT(*) FROM bp68_processed_cases")
total = cur.fetchone()[0]
print(f"Table created: bp68_processed_cases")
print(f"Backfilled   : {backfilled} cases from existing BP_68 links")
print(f"Total tracked: {total} cases")

cur.close()
conn.close()
