import psycopg2
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
conn.set_session(isolation_level=psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED)
cur = conn.cursor()

print("="*70)
print("HISTORICAL GHOST FLEET DEEP DIAGNOSTIC")
print("="*70)

# 1. Check total and completed
print("\n[1] OVERALL STATUS")
cur.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE digest_facts IS NOT NULL) as has_digest,
        COUNT(*) FILTER (WHERE ai_model LIKE '%BLOCKED%') as safety_blocked,
        COUNT(*) FILTER (WHERE ai_model = 'gemini-2.5-flash-lite') as flash_lite,
        COUNT(*) FILTER (WHERE ai_model = 'gemini-3-flash-preview') as flash_3
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND date >= '1901-01-01'
      AND date < '1987-01-01'
""")
row = cur.fetchone()
print(f"Total Cases: {row[0]}")
print(f"Has Digest: {row[1]}")
print(f"Safety Blocked: {row[2]}")
print(f"Flash Lite Digested: {row[3]}")
print(f"Flash 3 Digested: {row[4]}")

# 2. Sample unprocessed cases
print("\n[2] SAMPLE UNPROCESSED CASES (First 5)")
cur.execute("""
    SELECT id, substring(short_title, 1, 40), date, ai_model, LENGTH(full_text_md)
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND date >= '1901-01-01'
      AND date < '1987-01-01'
      AND (ai_model IS NULL OR ai_model NOT LIKE '%gemini%')
    ORDER BY id
    LIMIT 5
""")
print(f"{'ID':<8} {'Title':<40} {'Date':<12} {'AI Model':<20} {'Size':<10}")
print("-" * 100)
for row in cur.fetchall():
    model = row[3] if row[3] else 'NULL'
    print(f"{row[0]:<8} {row[1]:<40} {str(row[2]):<12} {model:<20} {row[4]:<10}")

# 3. Check if there are any "stuck" cases being claimed but not completed
print("\n[3] RECENTLY UPDATED CASES (Last 10 updates)")
cur.execute("""
    SELECT id, substring(short_title, 1, 40), ai_model, updated_at
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND date >= '1901-01-01'
      AND date < '1987-01-01'
    ORDER BY updated_at DESC NULLS LAST
    LIMIT 10
""")
print(f"{'ID':<8} {'Title':<40} {'AI Model':<25} {'Updated At':<20}")
print("-" * 100)
for row in cur.fetchall():
    model = row[2] if row[2] else 'NULL'
    updated = str(row[3]) if row[3] else 'NULL'
    print(f"{row[0]:<8} {row[1]:<40} {model:<25} {updated:<20}")

conn.close()
