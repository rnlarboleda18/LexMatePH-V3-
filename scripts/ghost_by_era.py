import psycopg2
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

print("GHOST CASES BY ERA")
print("="*60)

# Historical vs Modern breakdown
cur.execute("""
    SELECT 
        CASE 
            WHEN date < '1987-01-01' THEN 'Historical (1901-1986)'
            WHEN date >= '1987-01-01' THEN 'Modern (1987-2025)'
            ELSE 'NULL Date'
        END as era,
        COUNT(*) as count,
        COUNT(*) FILTER (WHERE digest_facts IS NULL) as missing_digest
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
    GROUP BY 1
    ORDER BY 1
""")

print(f"{'Era':<30} | {'Total':<8} | {'No Digest':<10}")
print("-" * 60)
total_all = 0
total_missing = 0
for row in cur.fetchall():
    print(f"{row[0]:<30} | {row[1]:<8,} | {row[2]:<10,}")
    total_all += row[1]
    total_missing += row[2]

print("-" * 60)
print(f"{'TOTAL':<30} | {total_all:<8,} | {total_missing:<10,}")

conn.close()
