"""How many pre-2019 cases are plausible RCC / BP 68 candidates."""
import json, psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor(cursor_factory=RealDictCursor)

# How many cases already linked to RCC, by year
cur.execute("""
    SELECT EXTRACT(YEAR FROM s.date)::int AS year,
           COUNT(DISTINCT l.case_id) AS linked
    FROM codal_case_links l
    JOIN sc_decided_cases s ON s.id = l.case_id
    WHERE l.statute_id = 'RCC' AND s.date IS NOT NULL
    GROUP BY year ORDER BY year
""")
print("Current RCC links by year:")
for r in cur.fetchall():
    print(f"  {r['year']}: {r['linked']} cases")

# Keyword search: how many pre-2019 cases mention corporation-law terms
keywords = [
    'corporation code', 'batas pambansa 68', 'b.p. 68', 'b.p. blg. 68',
    'bp blg. 68', 'bp 68', 'corporate officer', 'board of directors',
    'piercing the corporate veil', 'derivative suit', 'stockholder',
    'corporate secretary', 'articles of incorporation'
]
like_clauses = " OR ".join(
    "LOWER(full_text_md) LIKE %s" for _ in keywords
)
params = [f"%{k}%" for k in keywords]

cur.execute(f"""
    SELECT EXTRACT(YEAR FROM date)::int AS year, COUNT(*) AS n
    FROM sc_decided_cases
    WHERE date >= '1980-01-01' AND date < '2019-01-01'
      AND ({like_clauses})
    GROUP BY year ORDER BY year
""", params)

rows = cur.fetchall()
total = sum(r["n"] for r in rows)
print(f"\nPre-2019 cases (1980-2018) with corporate-law keywords: {total:,}")
print("By decade:")
decades = {}
for r in rows:
    d = (r["year"] // 10) * 10
    decades[d] = decades.get(d, 0) + r["n"]
for d, n in sorted(decades.items()):
    print(f"  {d}s: {n:,}")

# Total pre-2019 SC cases for context
cur.execute("""
    SELECT COUNT(*) AS n FROM sc_decided_cases
    WHERE date >= '1980-01-01' AND date < '2019-01-01'
""")
print(f"\nTotal SC cases 1980-2018: {cur.fetchone()['n']:,}")

conn.close()
