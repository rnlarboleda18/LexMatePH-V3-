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

print("EXTRACTING PHASE 2 CASES FOR PRO FLEETS")
print("=" * 60)

# 1. Ultra-Large (500K-1M) for gemini-3-pro-preview
print("\n[1] Ultra-Large Cases (500K-1M)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) >= 500000
      AND LENGTH(full_text_md) <= 1000000
      AND (ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL)
    ORDER BY id
""")
ultra_cases = [row[0] for row in cur.fetchall()]
print(f"Total: {len(ultra_cases)}")

# Partition into 2 workers
for i in range(2):
    start = i * math.ceil(len(ultra_cases) / 2)
    end = min(start + math.ceil(len(ultra_cases) / 2), len(ultra_cases))
    batch = ultra_cases[start:end]
    
    if batch:
        with open(f"phase2_ultra_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
print("Created 2 batch files for Ultra-Large fleet")

# 2. Mid-Large (200K-500K) for gemini-2.5-pro
print("\n[2] Mid-Large Cases (200K-500K)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) >= 200000
      AND LENGTH(full_text_md) < 500000
      AND (ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL)
      AND (ai_model NOT LIKE '%gemini-2.5-pro%' OR ai_model IS NULL)
    ORDER BY id
""")
mid_cases = [row[0] for row in cur.fetchall()]
print(f"Total: {len(mid_cases)}")

# Partition into 5 workers
for i in range(5):
    start = i * math.ceil(len(mid_cases) / 5)
    end = min(start + math.ceil(len(mid_cases) / 5), len(mid_cases))
    batch = mid_cases[start:end]
    
    if batch:
        with open(f"phase2_mid_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
print("Created 5 batch files for Mid-Large fleet")

print("\n" + "=" * 60)
print("READY TO LAUNCH PRO FLEETS")
conn.close()
