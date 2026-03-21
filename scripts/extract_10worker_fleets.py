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

print("EXTRACTING FOR 10-WORKER FLEETS")
print("=" * 60)

# 1. TURBO FLEET - Remaining En Banc Phase 1 cases
print("\n[1] TURBO FLEET (En Banc < 100K)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) < 100000
      AND (ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL)
    ORDER BY id
""")
turbo_cases = [row[0] for row in cur.fetchall()]
print(f"Total Cases: {len(turbo_cases)}")

# Partition into 10 workers
for i in range(10):
    start = i * math.ceil(len(turbo_cases) / 10)
    end = min(start + math.ceil(len(turbo_cases) / 10), len(turbo_cases))
    batch = turbo_cases[start:end]
    
    if batch:
        with open(f"turbo_10w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
print("Created 10 batch files for Turbo Fleet")

# 2. GHOST FLEET - Remaining Ghost cases
print("\n[2] GHOST FLEET (Null Division)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND (ai_model NOT LIKE '%gemini-2.5-flash-lite%' OR ai_model IS NULL)
    ORDER BY id
""")
ghost_cases = [row[0] for row in cur.fetchall()]
print(f"Total Cases: {len(ghost_cases)}")

# Partition into 10 workers
for i in range(10):
    start = i * math.ceil(len(ghost_cases) / 10)
    end = min(start + math.ceil(len(ghost_cases) / 10), len(ghost_cases))
    batch = ghost_cases[start:end]
    
    if batch:
        with open(f"ghost_10w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
print("Created 10 batch files for Ghost Fleet")

print("\n" + "=" * 60)
print("READY TO LAUNCH")
conn.close()
