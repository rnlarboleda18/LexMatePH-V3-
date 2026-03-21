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

print("EXTRACTING PRO FLEETS (5 WORKERS EACH)")
print("=" * 60)

# 1. Ultra-Large (500K-1M)
print("\n[1] ULTRA-LARGE (500K-1M)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) >= 500000
      AND LENGTH(full_text_md) <= 1000000
    ORDER BY id
""")
ultra_cases = [row[0] for row in cur.fetchall()]
print(f"Total Ultra Cases: {len(ultra_cases)}")

# Partition Ultra into 5
for i in range(5):
    start = i * math.ceil(len(ultra_cases) / 5)
    end = min(start + math.ceil(len(ultra_cases) / 5), len(ultra_cases))
    batch = ultra_cases[start:end]
    if batch:
        with open(f"phase2_ultra_5w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")

# 2. Mid-Large (200K-500K)
print("\n[2] MID-LARGE (200K-500K)")
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE division = 'En Banc'
      AND date >= '1987-01-01'
      AND LENGTH(full_text_md) >= 200000
      AND LENGTH(full_text_md) < 500000
    ORDER BY id
""")
mid_cases = [row[0] for row in cur.fetchall()]
print(f"Total Mid-Large Cases: {len(mid_cases)}")

# Partition Mid into 5
for i in range(5):
    start = i * math.ceil(len(mid_cases) / 5)
    end = min(start + math.ceil(len(mid_cases) / 5), len(mid_cases))
    batch = mid_cases[start:end]
    if batch:
        with open(f"phase2_mid_5w_{i+1:02d}.txt", 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")

print(f"\nCreated batch files for 5 workers each")
conn.close()
