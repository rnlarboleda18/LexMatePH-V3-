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
print("EXTRACTING HISTORICAL CASES FOR ENHANCED BACKFILL")
print("="*70 + "\n")

# Target: 1901-1986 cases with ANY missing enhanced field
# Fields: legal_concepts, flashcards, cited_cases, timeline, statutes_involved (adding statutes just in case)

cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
      AND (
          legal_concepts IS NULL OR legal_concepts::text = '[]' OR legal_concepts::text = '{}' OR
          flashcards IS NULL OR flashcards::text = '[]' OR flashcards::text = '{}' OR
          cited_cases IS NULL OR cited_cases::text = '[]' OR cited_cases::text = '{}' OR
          timeline IS NULL OR timeline::text = '[]' OR timeline::text = '{}'
      )
    ORDER BY id
""")
cases = [row[0] for row in cur.fetchall()]
total = len(cases)

print(f"Total Cases to Backfill: {total}")

if total == 0:
    print("No cases found matching criteria.")
    exit()

# Partition into 50 workers
num_workers = 50
cases_per_worker = math.ceil(total / num_workers)

print(f"Partitioning into {num_workers} workers (~{cases_per_worker} cases each)...")

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, total)
    batch = cases[start:end]
    
    if batch:
        filename = f"historical_backfill_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
        # print(f"  {filename}: {len(batch)} cases")

print(f"Created 50 batch files (historical_backfill_xx.txt).")
print(f"\n{'='*70}")
print("READY FOR LAUNCH")
print("="*70)
print(f"Model: gemini-2.5-flash-lite")
print(f"Workers: 50")
print(f"Total Target: {total} cases")
print("="*70 + "\n")

conn.close()
