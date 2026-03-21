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

print("REORGANIZED GHOST STRATEGY - EXTRACTION")
print("="*70)

# 1. Historical Ghost Cases (1901-1986) - Redigest with 2.5-flash-lite
print("\n[1] HISTORICAL GHOST CASES (1901-1986)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND date >= '1901-01-01'
      AND date < '1987-01-01'
    ORDER BY id
""")
hist_ghost = [row[0] for row in cur.fetchall()]
print(f"Total: {len(hist_ghost)}")

# Partition into 5 workers
for i in range(5):
    start = i * math.ceil(len(hist_ghost) / 5)
    end = min(start + math.ceil(len(hist_ghost) / 5), len(hist_ghost))
    batch = hist_ghost[start:end]
    
    if batch:
        with open(f"hist_ghost_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
print("Created 5 batch files for Historical Ghost fleet")

# 2. Modern Ghost Cases (1987-2025) - Exclude gpt-5-mini, merge with En Banc
print("\n[2] MODERN GHOST CASES (1987-2025) - Excluding GPT-5-mini")
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

# 3. En Banc Cases (existing Turbo target)
print("\n[3] EN BANC CASES (Turbo Fleet)")
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

# 4. MERGE Modern Ghost + En Banc for 20-worker Turbo fleet
merged = sorted(set(modern_ghost + en_banc))
print(f"\n[4] MERGED TURBO FLEET (En Banc + Modern Ghost)")
print(f"Total: {len(merged)}")

# Partition into 20 workers
for i in range(20):
    start = i * math.ceil(len(merged) / 20)
    end = min(start + math.ceil(len(merged) / 20), len(merged))
    batch = merged[start:end]
    
    if batch:
        with open(f"turbo_20w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
print("Created 20 batch files for Merged Turbo fleet")

print("\n" + "="*70)
print("READY TO LAUNCH")
conn.close()
