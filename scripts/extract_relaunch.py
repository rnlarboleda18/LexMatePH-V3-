import psycopg2
import json
import math
import os

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

def partition_and_save(cases, prefix, num_workers):
    total = len(cases)
    print(f"\nProcessing {prefix} ({total} cases) -> {num_workers} workers")
    
    if total == 0:
        print("  No cases found.")
        return

    cases_per_worker = math.ceil(total / num_workers)
    
    for i in range(num_workers):
        start = i * cases_per_worker
        end = min(start + cases_per_worker, total)
        batch = cases[start:end]
        
        filename = f"{prefix}_{i+1:02d}.txt"
        with open(filename, 'w') as f:
            for case_id in batch:
                f.write(f"{case_id}\n")
    print(f"  Created {num_workers} files.")

print("EXTRACTING & PARTITIONING FOR RELAUNCH")

# 1. TURBO FLEET (En Banc Phase 1) - 25 Workers
# Criteria: En Banc, >= 1987, < 100K chars
# Exclude: Already has a gemini-3 digest
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
partition_and_save(turbo_cases, "turbo_relaunch", 25)

# 2. GHOST FLEET (Repair) - 20 Workers
# Criteria: Ghost (Null Division)
# Exclude: Already has a gemini-2.5-flash-lite digest (if backfill caught some)
# Note: User wants to force using gemini-2.5-flash-lite, so we exclude those already done by it? 
# The user said "relaunch... use gemini 2.5 flash lite". Let's assume we want to finish the job.
cur.execute("""
    SELECT id
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL)
      AND (ai_model NOT LIKE '%gemini-2.5-flash-lite%' OR ai_model IS NULL)
    ORDER BY id
""")
ghost_cases = [row[0] for row in cur.fetchall()]
partition_and_save(ghost_cases, "ghost_relaunch", 20)

conn.close()
