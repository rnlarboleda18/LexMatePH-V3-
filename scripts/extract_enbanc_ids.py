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

# Extract all En Banc 1987-2025 cases that need upgrade (pre-Gemini 3)
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc' 
      AND date >= '1987-01-01'
      AND date <= '2025-12-31'
      AND (ai_model IS NULL OR 
           ai_model NOT LIKE '%gemini-3%')
      AND digest_facts IS NOT NULL
    ORDER BY date DESC
""")

case_ids = [row[0] for row in cur.fetchall()]
total = len(case_ids)

print(f"\nExtracted {total:,} case IDs for En Banc upgrade")
print(f"Date range: 1987-2025")
print(f"Criteria: Pre-Gemini 3 models\n")

# Partition into 20 files for parallel processing
num_workers = 20
cases_per_worker = math.ceil(total / num_workers)

print(f"Partitioning into {num_workers} worker files...")
print(f"~{cases_per_worker:,} cases per worker\n")

for i in range(num_workers):
    start_idx = i * cases_per_worker
    end_idx = min(start_idx + cases_per_worker, total)
    batch_ids = case_ids[start_idx:end_idx]
    
    filename = f"enbanc_upgrade_batch_{i+1:02d}.txt"
    with open(filename, 'w') as f:
        for case_id in batch_ids:
            f.write(f"{case_id}\n")
    
    print(f"✅ {filename}: {len(batch_ids):,} cases")

print(f"\n{'='*60}")
print(f"READY FOR DEPLOYMENT")
print(f"{'='*60}")
print(f"Total cases: {total:,}")
print(f"Workers: {num_workers}")
print(f"Model: gemini-2.0-flash")
print(f"ETA: ~22 hours")
print(f"Cost: ~$1,200")
print(f"{'='*60}\n")

conn.close()
