import json, psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT
        l.statute_id,
        MIN(EXTRACT(YEAR FROM s.date)::int) AS first_year,
        MAX(EXTRACT(YEAR FROM s.date)::int) AS last_year,
        COUNT(DISTINCT l.case_id)           AS linked_cases,
        COUNT(*)                             AS total_links
    FROM codal_case_links l
    JOIN sc_decided_cases s ON s.id = l.case_id
    WHERE s.date IS NOT NULL
    GROUP BY l.statute_id
    ORDER BY l.statute_id
""")

rows = cur.fetchall()
conn.close()

print(f"{'STATUTE':<22} {'FIRST':>6} {'LAST':>6} {'SPAN':>6} {'LINKED CASES':>13} {'TOTAL LINKS':>12}")
print("-" * 70)
for r in rows:
    span = r["last_year"] - r["first_year"]
    print(f"{r['statute_id']:<22} {r['first_year']:>6} {r['last_year']:>6} {span:>5}y {r['linked_cases']:>13,} {r['total_links']:>12,}")
