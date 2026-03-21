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
print("EXTRACTING REMAINING HISTORICAL CASES")
print("="*70 + "\n")

# Extract remaining cases
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND digest_facts IS NOT NULL
      AND (digest_ratio IS NULL OR digest_ratio = '')
    ORDER BY id
""")
remaining_ids = [row[0] for row in cur.fetchall()]

total = len(remaining_ids)
print(f"Remaining cases: {total}")

if total == 0:
    print("No cases remaining! Fleet is complete.")
    exit()

# Partition into 5 workers
num_workers = 5
cases_per_worker = math.ceil(total / num_workers)

print(f"Partitioning into {num_workers} workers (~{cases_per_worker} cases each)...")

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = remaining_ids[start:end]
    
    if batch:
        filename = f"historical_remaining_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
        print(f"  {filename}: {len(batch)} cases")

print(f"\n{'='*70}")
print("READY FOR REDEPLOYMENT")
print("="*70)
print(f"Model: gemini-2.5-flash")
print(f"Workers: 5")
print("="*70 + "\n")

conn.close()
