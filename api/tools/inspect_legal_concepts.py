import json, psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor(cursor_factory=RealDictCursor)

for tbl in ["jurisprudence_links", "flashcard_concepts"]:
    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
    """, (tbl,))
    cols = cur.fetchall()
    print(f"\n{tbl} columns:")
    for c in cols:
        print(f"  {c['column_name']} ({c['data_type']})")
    cur.execute(f"SELECT COUNT(*) AS n FROM {tbl}")
    print(f"  rows: {cur.fetchone()['n']}")
    cur.execute(f"SELECT * FROM {tbl} LIMIT 3")
    for r in cur.fetchall():
        print(" ", {k: str(v)[:80] for k, v in dict(r).items()})

conn.close()
