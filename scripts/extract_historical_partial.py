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

# Extract the 51 cases needing partial redigestion
cur.execute("""
    SELECT id, short_title, date, EXTRACT(YEAR FROM date)::INT as year
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND digest_facts IS NOT NULL
      AND (
          digest_issues IS NULL OR
          digest_ruling IS NULL OR
          digest_ratio IS NULL OR
          main_doctrine IS NULL
      )
    ORDER BY date
""")

cases = cur.fetchall()

# Save to file
with open('historical_partial_redigestion_needed.txt', 'w') as f:
    for case_id, title, date, year in cases:
        f.write(f"{case_id}\n")

print(f"Saved {len(cases)} case IDs to: historical_partial_redigestion_needed.txt")
print(f"\nCase Details:")
for case_id, title, date, year in cases[:10]:  # Show first 10
    print(f"  {case_id} - {title[:50]} ({year})")
if len(cases) > 10:
    print(f"  ... and {len(cases) - 10} more")

conn.close()
