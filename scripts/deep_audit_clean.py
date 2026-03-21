import psycopg2
import json
from datetime import datetime, timedelta

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

print("\n" + "="*90)
print("DEEP AUDIT: HISTORICAL CASES (1901-1986)")
print("="*90)

# Get totals
cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986")
total = cur.fetchone()[0]

print(f"\nTotal Cases: {total:,}\n")

# Check critical digest fields
critical_fields = {
    'digest_facts': 'Facts',
    'digest_issues': 'Issues',
    'digest_ruling': 'Ruling',
    'digest_ratio': 'Ratio',
    'main_doctrine': 'Main Doctrine'
}

print("="*90)
print("CRITICAL DIGEST FIELDS STATUS")
print("="*90)
print(f"{'Field':<25} {'Missing':>15} {'Populated':>15} {'% Complete':>15}")
print("-" * 90)

critical_missing_count = 0

for field, label in critical_fields.items():
    cur.execute(f"""
        SELECT 
            COUNT(*) FILTER (WHERE {field} IS NULL OR {field} = '') as missing,
            COUNT(*) FILTER (WHERE {field} IS NOT NULL AND {field} != '') as populated
        FROM sc_decided_cases 
        WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
    """)
    
    missing, populated = cur.fetchone()
    pct = (populated / total * 100) if total > 0 else 0
    print(f"{label:<25} {missing:>15,} {populated:>15,} {pct:>14.1f}%")
    
    if missing > 0:
        critical_missing_count += missing

# Enhanced fields audit
print(f"\n{'='*90}")
print("ENHANCED FIELDS STATUS")
print("="*90)
print(f"{'Field':<25} {'Missing':>15} {'Populated':>15} {'% Complete':>15}")
print("-" * 90)

enhanced_fields = {
    'keywords': 'Keywords',
    'cited_cases': 'Cited Cases',
    'legal_concepts': 'Legal Concepts',
    'flashcards': 'Flashcards',
    'separate_opinions': 'Separate Opinions',
    'timeline': 'Timeline',
    'statutes_involved': 'Statutes Involved'
}

for field, label in enhanced_fields.items():
    cur.execute(f"""
        SELECT 
            COUNT(*) FILTER (WHERE {field} IS NULL OR {field}::text = '[]') as missing,
            COUNT(*) FILTER (WHERE {field} IS NOT NULL AND {field}::text != '[]') as populated
        FROM sc_decided_cases 
        WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
    """)
    
    missing, populated = cur.fetchone()
    pct = (populated / total * 100) if total > 0 else 0
    print(f"{label:<25} {missing:>15,} {populated:>15,} {pct:>14.1f}%")

# Cases with ANY critical field missing
cur.execute("""
    SELECT COUNT(*)
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND (digest_facts IS NULL OR digest_facts = '' OR
           digest_issues IS NULL OR digest_issues = '' OR
           digest_ruling IS NULL OR digest_ruling = '' OR
           digest_ratio IS NULL OR digest_ratio = '' OR
           main_doctrine IS NULL OR main_doctrine = '')
""")
any_critical_missing = cur.fetchone()[0]

print(f"\n{'='*90}")
print("SUMMARY")
print("="*90)
print(f"\nCases with ANY critical field missing: {any_critical_missing:,} ({any_critical_missing/total*100:.1f}%)")
print(f"Cases with ALL critical fields complete: {total - any_critical_missing:,} ({(total-any_critical_missing)/total*100:.1f}%)")

# Yesterday's ingestion check
yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0)
yesterday_end = yesterday_start.replace(hour=23, minute=59, second=59)

cur.execute(f"""
    SELECT COUNT(*)
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND created_at >= '{yesterday_start.strftime('%Y-%m-%d %H:%M:%S')}'
      AND created_at <= '{yesterday_end.strftime('%Y-%m-%d %H:%M:%S')}'
      AND full_text_md IS NOT NULL
""")
yesterday_total = cur.fetchone()[0]

cur.execute(f"""
    SELECT COUNT(*)
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND created_at >= '{yesterday_start.strftime('%Y-%m-%d %H:%M:%S')}'
      AND created_at <= '{yesterday_end.strftime('%Y-%m-%d %H:%M:%S')}'
      AND full_text_md IS NOT NULL
      AND digest_facts IS NOT NULL
""")
yesterday_digested = cur.fetchone()[0]

print(f"\n{'='*90}")
print("YESTERDAY'S INGESTION STATUS")
print("="*90)
print(f"\nCases with full_text_md created yesterday: {yesterday_total:,}")
if yesterday_total > 0:
    print(f"  - Already digested: {yesterday_digested:,} ({yesterday_digested/yesterday_total*100:.1f}%)")
    print(f"  - Need digestion: {yesterday_total - yesterday_digested:,} ({(yesterday_total-yesterday_digested)/yesterday_total*100:.1f}%)")
else:
    print("  - No cases ingested yesterday")

print("\n" + "="*90)
print("REDIGESTION RECOMMENDATIONS")
print("="*90)
print(f"\n1. Cases missing critical fields: {any_critical_missing:,}")
print(f"2. Yesterday's undigested backlog: {yesterday_total - yesterday_digested if yesterday_total > 0 else 0:,}")
print(f"3. TOTAL NEEDING WORK: {any_critical_missing + (yesterday_total - yesterday_digested if yesterday_total > 0 else 0):,}")
print("\n" + "="*90 + "\n")

conn.close()
