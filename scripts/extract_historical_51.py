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
print("EXTRACTING 51 HISTORICAL CASES BY COMPLEXITY")
print("="*70 + "\n")

# Simple cases (< 10K chars) - gemini-2.0-flash
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND digest_facts IS NOT NULL
      AND (digest_ratio IS NULL OR digest_ratio = '')
      AND LENGTH(full_text_md) < 10000
    ORDER BY id
""")
simple_ids = [row[0] for row in cur.fetchall()]

# Complex cases (>= 10K chars) - gemini-2.5-flash
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND digest_facts IS NOT NULL
      AND (digest_ratio IS NULL OR digest_ratio = '')
      AND LENGTH(full_text_md) >= 10000
    ORDER BY id
""")
complex_ids = [row[0] for row in cur.fetchall()]

print(f"Simple cases (< 10K chars): {len(simple_ids)} - Using gemini-2.0-flash")
print(f"Complex cases (>= 10K chars): {len(complex_ids)} - Using gemini-2.5-flash")
print(f"Total: {len(simple_ids) + len(complex_ids)}\n")

# Partition simple cases into 5 workers
num_simple_workers = 5
cases_per_simple_worker = math.ceil(len(simple_ids) / num_simple_workers)

print(f"Partitioning simple cases into {num_simple_workers} workers...")
for i in range(num_simple_workers):
    start = i * cases_per_simple_worker
    end = min(start + cases_per_simple_worker, len(simple_ids))
    batch = simple_ids[start:end]
    
    if batch:
        filename = f"historical_simple_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
        print(f"  {filename}: {len(batch)} cases")

# Partition complex cases into 5 workers
num_complex_workers = 5
cases_per_complex_worker = math.ceil(len(complex_ids) / num_complex_workers)

print(f"\nPartitioning complex cases into {num_complex_workers} workers...")
for i in range(num_complex_workers):
    start = i * cases_per_complex_worker
    end = min(start + cases_per_complex_worker, len(complex_ids))
    batch = complex_ids[start:end]
    
    if batch:
        filename = f"historical_complex_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
        print(f"  {filename}: {len(batch)} cases")

print(f"\n{'='*70}")
print("READY FOR DEPLOYMENT")
print("="*70)
print(f"Simple workers: 5 (gemini-2.0-flash)")
print(f"Complex workers: 5 (gemini-2.5-flash)")
print(f"Total workers: 10")
print(f"ETA: 2-5 minutes")
print("="*70 + "\n")

conn.close()
