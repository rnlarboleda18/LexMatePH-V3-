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
print("DEEP AUDIT: HISTORICAL CASES (1901-1986) - ALL FIELDS")
print("="*90 + "\n")

# Total cases in this period
cur.execute("""
    SELECT COUNT(*) 
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
""")
total = cur.fetchone()[0]

print(f"Total Cases (1901-1986): {total:,}\n")

# Check each field individually
fields_to_audit = [
    # Core digest fields
    ('digest_facts', 'Facts', 'text'),
    ('digest_issues', 'Issues', 'text'),
    ('digest_ruling', 'Ruling', 'text'),
    ('digest_ratio', 'Ratio', 'text'),
    ('main_doctrine', 'Main Doctrine', 'text'),
    
    # Metadata fields
    ('significance_category', 'Significance Category', 'text'),
    ('ponente', 'Ponente', 'text'),
    ('division', 'Division', 'text'),
    
    # JSON array fields
    ('keywords', 'Keywords', 'json'),
    ('cited_cases', 'Cited Cases', 'json'),
    ('legal_concepts', 'Legal Concepts', 'json'),
    ('flashcards', 'Flashcards', 'json'),
    ('separate_opinions', 'Separate Opinions', 'json'),
    ('statutes_involved', 'Statutes', 'json'),
    ('timeline', 'Timeline', 'json'),
    ('secondary_rulings', 'Secondary Rulings', 'json'),
    
    # Other fields
    ('spoken_script', 'Spoken Script', 'text'),
    ('ai_model', 'AI Model Used', 'text'),
]

print("="*90)
print("FIELD-BY-FIELD ANALYSIS")
print("="*90)
print(f"{'Field':<30} | {'Missing':>10} | {'Empty':>10} | {'Populated':>10} | {'%':>6}")
print("-" * 90)

missing_by_field = {}

for field, label, field_type in fields_to_audit:
    if field_type == 'json':
        # JSON fields - check for NULL or empty arrays
        cur.execute(f"""
            SELECT 
                COUNT(*) FILTER (WHERE {field} IS NULL) as null_count,
                COUNT(*) FILTER (WHERE {field}::text = '[]') as empty_count,
                COUNT(*) FILTER (WHERE {field} IS NOT NULL AND {field}::text != '[]') as populated_count
            FROM sc_decided_cases 
            WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
        """)
    else:
        # Text fields - check for NULL or empty strings
        cur.execute(f"""
            SELECT 
                COUNT(*) FILTER (WHERE {field} IS NULL) as null_count,
                COUNT(*) FILTER (WHERE {field} = '') as empty_count,
                COUNT(*) FILTER (WHERE {field} IS NOT NULL AND {field} != '') as populated_count
            FROM sc_decided_cases 
            WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
        """)
    
    null_count, empty_count, populated_count = cur.fetchone()
    missing_total = null_count + empty_count
    pct_populated = (populated_count / total * 100) if total > 0 else 0
    
    missing_by_field[field] = missing_total
    
    # Flag critical missing fields
    if field in ['digest_facts', 'digest_issues', 'digest_ruling', 'digest_ratio'] and missing_total > 100:
        flag = "❌"
    elif missing_total > total * 0.5:  # More than 50% missing
        flag = "⚠️ "
    else:
        flag = "✅"
    
    print(f"{flag} {label:<28} | {null_count:>10,} | {empty_count:>10,} | {populated_count:>10,} | {pct_populated:>5.1f}%")

# Find cases missing CRITICAL fields
print(f"\n{'='*90}")
print("CRITICAL MISSING FIELDS (Facts, Issues, Ruling, Ratio)")
print("="*90)

cur.execute("""
    SELECT COUNT(*)
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND (
          digest_facts IS NULL OR digest_facts = '' OR
          digest_issues IS NULL OR digest_issues = '' OR
          digest_ruling IS NULL OR digest_ruling = '' OR
          digest_ratio IS NULL OR digest_ratio = ''
      )
""")
critical_missing = cur.fetchone()[0]

print(f"\nCases with ANY critical field missing: {critical_missing:,} ({critical_missing/total*100:.1f}%)")

# YESTERDAY'S INGESTION AUDIT
print(f"\n{'='*90}")
print("YESTERDAY'S INGESTION AUDIT")
print("="*90)

yesterday = datetime.now() - timedelta(days=1)
yesterday_start = yesterday.replace(hour=0, minute=0, second=0)
yesterday_end = yesterday.replace(hour=23, minute=59, second=59)

cur.execute(f"""
    SELECT COUNT(*)
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND created_at >= '{yesterday_start.strftime('%Y-%m-%d %H:%M:%S')}'
      AND created_at <= '{yesterday_end.strftime('%Y-%m-%d %H:%M:%S')}'
      AND full_text_md IS NOT NULL
""")
yesterday_ingested = cur.fetchone()[0]

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

yesterday_not_digested = yesterday_ingested - yesterday_digested

print(f"\nCases ingested yesterday (with full_text_md): {yesterday_ingested:,}")
if yesterday_ingested > 0:
    print(f"  - With digest: {yesterday_digested:,} ({yesterday_digested/yesterday_ingested*100:.1f}%)")
    print(f"  - Without digest: {yesterday_not_digested:,} ({yesterday_not_digested/yesterday_ingested*100:.1f}%)")
else:
    print("  - No cases ingested yesterday")

# RECOMMENDATIONS
print(f"\n{'='*90}")
print("REDIGESTION RECOMMENDATIONS")
print("="*90)

print(f"\n1. CRITICAL PRIORITY: {critical_missing:,} cases missing core digest fields")
print(f"2. YESTERDAY'S BACKLOG: {yesterday_not_digested:,} cases ingested but not digested")
print(f"3. TOTAL NEEDING WORK: {critical_missing + yesterday_not_digested:,} cases")

print("\n" + "="*90 + "\n")

conn.close()
