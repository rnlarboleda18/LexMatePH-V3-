"""
Audit: codal_case_links — linked cases per year, per statute.
Run: api/.venv/Scripts/python api/tools/audit_codal_links_per_year.py
"""
import json, os, sys
from pathlib import Path
from psycopg2.extras import RealDictCursor
import psycopg2

API_ROOT = Path(__file__).resolve().parent.parent
with open(API_ROOT / "local.settings.json", encoding="utf-8") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor(cursor_factory=RealDictCursor)

# -- Schema check ------------------------------------------------------------
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'codal_case_links'
    ORDER BY ordinal_position
""")
print("codal_case_links columns:", [r["column_name"] for r in cur.fetchall()])

# -- Totals -------------------------------------------------------------------
cur.execute("SELECT COUNT(*) AS n FROM codal_case_links")
total_links = cur.fetchone()["n"]

cur.execute("SELECT COUNT(DISTINCT case_id) AS n FROM codal_case_links")
total_linked_cases = cur.fetchone()["n"]

cur.execute("SELECT COUNT(*) AS n FROM sc_decided_cases")
total_cases = cur.fetchone()["n"]

print(f"\n{'='*60}")
print(f"CODAL CASE LINKS - FULL AUDIT")
print(f"{'='*60}")
print(f"Total SC cases in DB   : {total_cases:,}")
print(f"Total linked cases     : {total_linked_cases:,}  ({100*total_linked_cases/max(total_cases,1):.1f}% coverage)")
print(f"Total link records     : {total_links:,}")

# -- Per statute totals -------------------------------------------------------
cur.execute("""
    SELECT statute_id,
           COUNT(*) AS total_links,
           COUNT(DISTINCT case_id) AS linked_cases
    FROM codal_case_links
    GROUP BY statute_id
    ORDER BY statute_id
""")
statute_rows = cur.fetchall()
print(f"\n{'-'*60}")
print(f"{'STATUTE':<20} {'LINKED CASES':>13} {'TOTAL LINKS':>12}")
print(f"{'-'*60}")
for r in statute_rows:
    print(f"{r['statute_id']:<20} {r['linked_cases']:>13,} {r['total_links']:>12,}")

# -- Per year (all statutes combined) ----------------------------------------
cur.execute("""
    SELECT EXTRACT(YEAR FROM s.date)::int AS year,
           COUNT(DISTINCT l.case_id)      AS linked_cases,
           COUNT(*)                        AS total_links
    FROM codal_case_links l
    JOIN sc_decided_cases s ON s.id = l.case_id
    WHERE s.date IS NOT NULL
    GROUP BY year
    ORDER BY year
""")
year_rows = cur.fetchall()

# Total cases per year for coverage %
cur.execute("""
    SELECT EXTRACT(YEAR FROM date)::int AS year,
           COUNT(*) AS total
    FROM sc_decided_cases
    WHERE date IS NOT NULL
    GROUP BY year
    ORDER BY year
""")
year_totals = {r["year"]: r["total"] for r in cur.fetchall()}

print(f"\n{'-'*60}")
print(f"LINKED CASES PER YEAR (all statutes)")
print(f"{'-'*60}")
print(f"{'YEAR':<6} {'TOTAL CASES':>12} {'LINKED CASES':>13} {'COVERAGE':>10} {'LINKS':>8}")
print(f"{'-'*60}")
for r in year_rows:
    yr = r["year"]
    tot = year_totals.get(yr, 0)
    pct = 100 * r["linked_cases"] / max(tot, 1)
    print(f"{yr:<6} {tot:>12,} {r['linked_cases']:>13,} {pct:>9.1f}% {r['total_links']:>8,}")

# -- Per year × per statute ---------------------------------------------------
cur.execute("""
    SELECT EXTRACT(YEAR FROM s.date)::int AS year,
           l.statute_id,
           COUNT(DISTINCT l.case_id) AS linked_cases,
           COUNT(*) AS total_links
    FROM codal_case_links l
    JOIN sc_decided_cases s ON s.id = l.case_id
    WHERE s.date IS NOT NULL
    GROUP BY year, l.statute_id
    ORDER BY year, l.statute_id
""")
year_statute_rows = cur.fetchall()

statutes = sorted({r["statute_id"] for r in year_statute_rows})
print(f"\n{'-'*60}")
print(f"LINKED CASES PER YEAR × STATUTE (linked_cases / total_links)")
print(f"{'-'*60}")
# Build pivot
pivot = {}
for r in year_statute_rows:
    pivot.setdefault(r["year"], {})[r["statute_id"]] = (r["linked_cases"], r["total_links"])

header = f"{'YEAR':<6}" + "".join(f"{s:>18}" for s in statutes)
print(header)
print("-" * len(header))
for yr in sorted(pivot):
    row_str = f"{yr:<6}"
    for s in statutes:
        lc, tl = pivot[yr].get(s, (0, 0))
        row_str += f"{lc:>8}/{tl:<9}"
    print(row_str)

# -- Unlinked cases per year --------------------------------------------------
cur.execute("""
    SELECT EXTRACT(YEAR FROM date)::int AS year,
           COUNT(*) AS unlinked
    FROM sc_decided_cases
    WHERE date IS NOT NULL
      AND id NOT IN (SELECT DISTINCT case_id FROM codal_case_links)
    GROUP BY year
    ORDER BY year
""")
unlinked_rows = {r["year"]: r["unlinked"] for r in cur.fetchall()}

print(f"\n{'-'*60}")
print(f"UNLINKED CASES PER YEAR")
print(f"{'-'*60}")
print(f"{'YEAR':<6} {'TOTAL':>8} {'LINKED':>8} {'UNLINKED':>10} {'UNLINKED %':>11}")
print(f"{'-'*60}")
for yr in sorted(year_totals):
    tot = year_totals[yr]
    unlinked = unlinked_rows.get(yr, 0)
    linked_yr = next((r["linked_cases"] for r in year_rows if r["year"] == yr), 0)
    pct_unlinked = 100 * unlinked / max(tot, 1)
    print(f"{yr:<6} {tot:>8,} {linked_yr:>8,} {unlinked:>10,} {pct_unlinked:>10.1f}%")

conn.close()
print(f"\n{'='*60}")
print("Audit complete.")
