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

print("\n" + "="*70)
print("EXTRACTING GHOST CASES FOR REPAIR")
print("="*70 + "\n")

# Target: 1,335 Ghost Cases
# Criteria: Full Text MD is NOT NULL but Digest Facts IS NULL
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND digest_facts IS NULL
    ORDER BY id
""")
cases = [row[0] for row in cur.fetchall()]
total = len(cases)

print(f"Total Ghost Cases: {total}")

if total == 0:
    print("No cases found matching criteria.")
    exit()

# Partition into 20 workers
num_workers = 20
cases_per_worker = math.ceil(total / num_workers)

print(f"Partitioning into {num_workers} workers (~{cases_per_worker} cases each)...")

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = cases[start:end]
    
    if batch:
        filename = f"ghost_repair_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")

print(f"Created 20 batch files (ghost_repair_xx.txt).")
print(f"\n{'='*70}")
print("READY FOR LAUNCH")
print("="*70)
print(f"Model: gemini-2.0-flash")
print(f"Workers: 20")
print(f"Total Target: {total} cases")
print("="*70 + "\n")

conn.close()
