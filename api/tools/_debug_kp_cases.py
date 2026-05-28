"""Debug: why KP cases (Peregrina, Ledesma, Aquino v. Aure) are not appearing in I.C key_cases.

Steps:
1. Confirm the 6 codal_case_links for LGC/408 and LGC/412 exist.
2. Simulate the fetch_cases_for_topic provision-linked query (same WHERE clause).
3. Check if cases pass the main_doctrine / significance_category filter.
4. Inspect what fetch_cases_for_topic actually does for inline provisions.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.environ["DB_CONNECTION_STRING"])
cur = conn.cursor(cursor_factory=RealDictCursor)

KP_CASE_IDS = [24874, 31010, 48146]
KP_PROVISIONS = [
    ("LGC", "399"), ("LGC", "408"), ("LGC", "409"),
    ("LGC", "412"), ("LGC", "416"), ("LGC", "417"), ("LGC", "418"),
]

# 1. Confirm codal_case_links for all 7 LGC provisions
print("=== codal_case_links for I.C provisions ===")
for stat, prov in KP_PROVISIONS:
    cur.execute("""
        SELECT l.case_id, c.short_title, c.case_number, c.date
        FROM codal_case_links l
        JOIN sc_decided_cases c ON c.id = l.case_id
        WHERE l.statute_id = %s AND l.provision_id = %s
        ORDER BY c.date DESC
    """, (stat, prov))
    rows = cur.fetchall()
    print(f"  {stat}/{prov}: {len(rows)} linked")
    for r in rows:
        print(f"    id={r['case_id']} | {r['short_title']} | {r['case_number']} | {r['date']}")

# 2. Simulate the full provision-linked case query (as fetch_cases_for_topic does it)
print("\n=== Provision-linked query (no date/doctrine filter) ===")
params = []
clauses = []
for stat, prov in KP_PROVISIONS:
    clauses.append("(l.statute_id = %s AND l.provision_id = %s)")
    params += [stat, prov]

query = f"""
    SELECT DISTINCT c.id, c.short_title, c.case_number, c.date,
           c.main_doctrine IS NOT NULL AS has_doctrine,
           c.significance_category IS NOT NULL AS has_sig
    FROM sc_decided_cases c
    JOIN codal_case_links l ON l.case_id = c.id
    WHERE ({' OR '.join(clauses)})
    ORDER BY c.date DESC
"""
cur.execute(query, params)
rows = cur.fetchall()
print(f"  Total: {len(rows)} cases")
for r in rows:
    print(f"    id={r['id']} | {r['short_title']} | {r['case_number']} | {r['date']} | doctrine={r['has_doctrine']} | sig={r['has_sig']}")

# 3. With date + doctrine + sig filter (as fetch_cases_for_topic applies)
print("\n=== Provision-linked query WITH date/doctrine/sig filter ===")
query2 = f"""
    SELECT DISTINCT c.id, c.short_title, c.case_number, c.date
    FROM sc_decided_cases c
    JOIN codal_case_links l ON l.case_id = c.id
    WHERE ({' OR '.join(clauses)})
      AND c.date <= '2025-06-30'
      AND c.main_doctrine IS NOT NULL
      AND c.significance_category IS NOT NULL
    ORDER BY c.date DESC
"""
cur.execute(query2, params)
rows2 = cur.fetchall()
print(f"  Total passing filter: {len(rows2)} cases")
for r in rows2:
    print(f"    id={r['id']} | {r['short_title']} | {r['date']}")

# 4. Check the 3 target KP cases directly
print("\n=== Direct check on KP case IDs ===")
cur.execute("""
    SELECT id, short_title, case_number, date,
           main_doctrine IS NOT NULL AS has_doctrine,
           significance_category IS NOT NULL AS has_sig
    FROM sc_decided_cases
    WHERE id = ANY(%s)
""", (KP_CASE_IDS,))
for r in cur.fetchall():
    print(f"  id={r['id']} | {r['short_title']} | {r['date']} | doctrine={r['has_doctrine']} | sig={r['has_sig']}")

# 5. Check what the fetch_cases_for_topic code does with 'inline' source
print("\n=== Reproducing fetch_cases_for_topic linked_pairs logic ===")
print("The inline provisions have statute_id='LGC', provision_id='399','408','409','412','416','417','418'.")
print("Check: does fetch_cases_for_topic skip 'inline' sources when building linked_pairs?")
print("(Answer: read the function source - check for source filtering)")

cur.close()
conn.close()
print("\nDone.")
