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

# Extract Phase 1: Cases < 100K characters
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc' 
      AND date >= '1987-01-01'
      AND (ai_model IS NULL OR ai_model NOT LIKE '%gemini-3%')
      AND full_text_md IS NOT NULL
      AND LENGTH(full_text_md) < 100000
    ORDER BY LENGTH(full_text_md) ASC
""")

case_ids = [row[0] for row in cur.fetchall()]
total = len(case_ids)

print(f"\n{'='*70}")
print(f"PHASE 1: EXTRACTING SMALL CASES (< 100K chars)")
print(f"{'='*70}\n")
print(f"Extracted: {total:,} case IDs")
print(f"Target: 6,101 cases")
print(f"Match: {'✅ EXACT' if total == 6101 else '❌ MISMATCH'}\n")

# Partition into 10 workers
num_workers = 10
cases_per_worker = math.ceil(total / num_workers)

print(f"Partitioning into {num_workers} worker files...")
print(f"~{cases_per_worker:,} cases per worker\n")

for i in range(num_workers):
    start_idx = i * cases_per_worker
    end_idx = min(start_idx + cases_per_worker, total)
    batch_ids = case_ids[start_idx:end_idx]
    
    filename = f"phase1_batch_{i+1:02d}.txt"
    with open(filename, 'w') as f:
        for case_id in batch_ids:
            f.write(f"{case_id}\n")
    
    print(f"✅ {filename}: {len(batch_ids):,} cases")

# Save summary for reminder
with open('phase1_summary.txt', 'w') as f:
    f.write(f"Phase 1 Deployment: {total:,} cases < 100K chars\n")
    f.write(f"Workers: {num_workers}\n")
    f.write(f"Cases per worker: ~{cases_per_worker:,}\n")
    f.write(f"Model: gemini-3-flash-preview\n")
    f.write(f"\nREMINDER: After completion, digest remaining 466 cases:\n")
    f.write(f"  - 449 cases (100K-500K chars)\n")
    f.write(f"  - 17 cases (500K-1M chars)\n")

print(f"\n{'='*70}")
print(f"READY FOR PHASE 1 DEPLOYMENT")
print(f"{'='*70}")
print(f"Total cases: {total:,}")
print(f"Workers: {num_workers}")
print(f"Model: gemini-3-flash-preview")
print(f"ETA: ~8-10 hours")
print(f"{'='*70}\n")

conn.close()
