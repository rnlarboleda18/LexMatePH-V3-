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

print("EXTRACTING REMAINING GHOST CASES FOR 40-WORKER RELAUNCH")
print("=" * 60)

# Get remaining Ghost cases (NULL division, not yet processed by gemini-2.5-flash-lite)
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND (ai_model NOT LIKE '%gemini-2.5-flash-lite%' OR ai_model IS NULL)
    ORDER BY id
""")
cases = [row[0] for row in cur.fetchall()]
total = len(cases)

print(f"Total Remaining Ghost Cases: {total}")

if total == 0:
    print("No cases found. All ghosts may be busted!")
    exit()

# Partition into 40 workers
num_workers = 40
cases_per_worker = math.ceil(total / num_workers)

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = cases[start:end]
    
    if batch:
        filename = f"ghost_40workers_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")

print(f"Created 40 batch files")
print(f"Ready to launch 40 workers with gemini-2.5-flash-lite")
conn.close()
