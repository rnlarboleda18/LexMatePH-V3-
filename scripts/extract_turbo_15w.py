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

print("TURBO 15-WORKER EXTRACTION")
print("="*70)

# 1. Modern Ghost Cases (1987-2025) - Exclude gpt-5-mini
print("\n[1] MODERN GHOST CASES")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND date >= '1987-01-01'
      AND (ai_model NOT LIKE '%gpt-5-mini%' OR ai_model IS NULL)
      AND (ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL)
    ORDER BY id
""")
modern_ghost = [row[0] for row in cur.fetchall()]
print(f"Total Modern Ghost: {len(modern_ghost)}")

# 2. En Banc Cases (Turbo Target)
print("\n[2] EN BANC CASES (< 100K)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) < 100000
      AND (ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL)
    ORDER BY id
""")
en_banc = [row[0] for row in cur.fetchall()]
print(f"Total En Banc: {len(en_banc)}")

# 3. MERGE
merged = sorted(set(modern_ghost + en_banc))
print(f"\n[3] MERGED TURBO FLEET")
print(f"Total: {len(merged)}")

# Partition into 15 workers
num_workers = 15
cases_per_worker = math.ceil(len(merged) / num_workers)

for i in range(num_workers):
    start = i * cases_per_worker
    end = min(start + cases_per_worker, len(merged))
    batch = merged[start:end]
    
    if batch:
        with open(f"turbo_15w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")

print(f"Created {num_workers} batch files")
conn.close()
