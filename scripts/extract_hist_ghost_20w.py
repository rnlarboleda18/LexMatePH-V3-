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

print("EXTRACTING HISTORICAL GHOST FOR 20 WORKERS")
print("=" * 60)

# Get Historical Ghost cases (1901-1986, NULL division)
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND date >= '1901-01-01'
      AND date < '1987-01-01'
    ORDER BY id
""")
cases = [row[0] for row in cur.fetchall()]
total = len(cases)

print(f"Total Historical Ghost Cases: {total}")

# Partition into 20 workers
num_workers = 20
cases_per_worker = math.ceil(total / num_workers)

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = cases[start:end]
    
    if batch:
        with open(f"hist_ghost_20w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")

print(f"Created 20 batch files")
print(f"Ready to launch 20 workers with gemini-2.5-flash-lite")
conn.close()
