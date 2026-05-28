"""Debug: find what provisions People v. XXX262846 is linked to, and what
cases are linked to the VIII.E provision set."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.environ["DB_CONNECTION_STRING"])
cur = conn.cursor(cursor_factory=RealDictCursor)

# 1. Find the case id for People v. XXX262846
cur.execute("""
    SELECT id, short_title, case_number, date
    FROM sc_decided_cases
    WHERE short_title ILIKE '%262846%' OR case_number ILIKE '%262846%'
    LIMIT 5
""")
print("=== People v. XXX262846 ===")
rows = cur.fetchall()
for r in rows:
    print(f"  id={r['id']} | {r['short_title']} | {r['case_number']} | {r['date']}")

if rows:
    case_id = rows[0]['id']
    cur.execute("""
        SELECT statute_id, provision_id
        FROM codal_case_links
        WHERE case_id = %s
    """, (case_id,))
    links = cur.fetchall()
    print(f"  Links ({len(links)}):")
    for l in links:
        print(f"    {l['statute_id']} / {l['provision_id']}")

# 2. What cases are linked to VIII.E provisions?
print("\n=== Cases linked to VIII.E provisions ===")
provisions = [
    ("ROC", "117-3"), ("ROC", "118-1"), ("ROC", "119-17"),
    ("ROC", "119-23"), ("ROC", "120-1"), ("ROC", "120-4"),
    ("CONST", "III-21"),
]
for statute_id, provision_id in provisions:
    cur.execute("""
        SELECT c.short_title, c.case_number, c.date
        FROM sc_decided_cases c
        JOIN codal_case_links l ON l.case_id = c.id
        WHERE l.statute_id = %s AND l.provision_id = %s
        AND c.date <= '2025-06-30'
        ORDER BY c.date DESC LIMIT 5
    """, (statute_id, provision_id))
    cases = cur.fetchall()
    print(f"\n  {statute_id}/{provision_id} — {len(cases)} cases")
    for c in cases:
        print(f"    {c['short_title']} | {c['case_number']} | {c['date']}")

# 3. Also check Reyes v. Sandiganbayan linkage
print("\n=== Reyes v. Sandiganbayan links ===")
cur.execute("""
    SELECT c.id, c.short_title, c.date
    FROM sc_decided_cases c
    WHERE c.short_title ILIKE '%Reyes%Sandiganbayan%' OR c.short_title ILIKE '%Sandiganbayan%Reyes%'
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"  {r['short_title']} | {r['date']}")
    cur.execute("SELECT statute_id, provision_id FROM codal_case_links WHERE case_id=%s", (r['id'],))
    for l in cur.fetchall():
        print(f"    → {l['statute_id']} / {l['provision_id']}")

cur.close(); conn.close()
print("\nDone.")
