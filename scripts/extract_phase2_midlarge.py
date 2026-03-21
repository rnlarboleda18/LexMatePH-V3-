import psycopg2
import json
import math

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

print("EXTRACTING PHASE 2 MID-LARGE CASES (200K-500K)")
print("=" * 50)

# Get cases in the 200K-500K range
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc' 
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) >= 200000
      AND LENGTH(full_text_md) < 500000
      AND (ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL)
    ORDER BY id
""")
cases = [row[0] for row in cur.fetchall()]
total = len(cases)

print(f"Total Cases: {total}")

if total == 0:
    print("No cases found.")
    exit()

# Partition into 5 workers
num_workers = 5
cases_per_worker = math.ceil(total / num_workers)

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = cases[start:end]
    
    if batch:
        filename = f"phase2_midlarge_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
        print(f"Created {filename}: {len(batch)} cases")

print(f"\nReady to launch 5 workers with gemini-2.5-pro")
conn.close()
