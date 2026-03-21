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

print("EXTRACTING MID-LARGE FOR 2 WORKERS")
print("=" * 60)

# Get Mid-Large cases (200K-500K, En Banc, 1987+)
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) >= 200000
      AND LENGTH(full_text_md) < 500000
    ORDER BY id
""")
cases = [row[0] for row in cur.fetchall()]
total = len(cases)

print(f"Total Mid-Large Cases: {total}")

# Partition into 2 workers
num_workers = 2
cases_per_worker = math.ceil(total / num_workers)

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = cases[start:end]
    
    if batch:
        with open(f"phase2_mid_2w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")

print(f"Created 2 batch files")
print(f"Ready to launch 2 workers with gemini-2.5-pro")
conn.close()
