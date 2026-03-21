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
print("EXTRACTING PHASE 1 REMAINING for TURBO MODE (30 WORKERS)")
print("="*70 + "\n")

# Get pending cases (< 100K chars)
# Exclude cases that are already fully processed
# Criteria: < 100K chars, En Banc, 1987-2025, AND (ai_model IS NULL OR ai_model NOT LIKE '%gemini-3%')
# Actually, the most reliable check is: Is it in the target set AND not digested?
# Target set: En Banc, 1987-2025, < 100K chars
# Digested check: digest_facts IS NULL OR ai_model NOT LIKE '%gemini-3%'

cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND date <= '2025-12-31'
      AND LENGTH(full_text_md) < 100000
      AND (
          digest_facts IS NULL 
          OR ai_model IS NULL 
          OR ai_model NOT LIKE '%gemini-3%'
      )
    ORDER BY id
""")
cases = [row[0] for row in cur.fetchall()]
total = len(cases)

print(f"Total Remaining Cases: {total}")

if total == 0:
    print("No cases remaining! Phase 1 complete.")
    exit()

# Partition into 30 workers
num_workers = 30
cases_per_worker = math.ceil(total / num_workers)

print(f"Partitioning into {num_workers} workers (~{cases_per_worker} cases each)...")

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = cases[start:end]
    
    if batch:
        filename = f"turbo_phase1_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
        # print(f"  {filename}: {len(batch)} cases")

print(f"Created 30 batch files (turbo_phase1_xx.txt).")
print(f"\n{'='*70}")
print("READY FOR TURBO LAUNCH")
print("="*70)
print(f"Model: gemini-3-flash-preview")
print(f"Workers: 30")
print(f"Total Target: {total} cases")
print("="*70 + "\n")

conn.close()
