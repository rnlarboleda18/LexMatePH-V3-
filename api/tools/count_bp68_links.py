import json, psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT COUNT(DISTINCT case_id) AS cases, COUNT(*) AS links
    FROM codal_case_links WHERE decided_under = 'BP_68'
""")
r = cur.fetchone()
print(f"Cases linked : {r['cases']}")
print(f"Total links  : {r['links']}")
conn.close()
