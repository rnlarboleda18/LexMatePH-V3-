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

# Select 10 large En Banc cases (by full_text_md length) that need upgrade
cur.execute("""
    SELECT 
        id,
        short_title,
        date,
        LENGTH(full_text_md) as text_length
    FROM sc_decided_cases 
    WHERE division = 'En Banc' 
      AND date >= '1987-01-01'
      AND (ai_model IS NULL OR ai_model NOT LIKE '%gemini-3%')
      AND full_text_md IS NOT NULL
    ORDER BY LENGTH(full_text_md) DESC
    LIMIT 10
""")

cases = cur.fetchall()

print("\n" + "="*80)
print("10 LARGEST EN BANC CASES FOR GEMINI-3-FLASH-PREVIEW TEST")
print("="*80 + "\n")
print(f"{'ID':<8} | {'Date':<12} | {'Size (chars)':>12} | {'Title'}")
print("-" * 80)

test_ids = []
for case_id, title, date, length in cases:
    print(f"{case_id:<8} | {str(date):<12} | {length:>12,} | {title[:40]}")
    test_ids.append(str(case_id))

# Save to file
with open('large_test_batch.txt', 'w') as f:
    for case_id in test_ids:
        f.write(f"{case_id}\n")

print("\n" + "="*80)
print(f"Saved {len(test_ids)} IDs to: large_test_batch.txt")
print("="*80 + "\n")

conn.close()
