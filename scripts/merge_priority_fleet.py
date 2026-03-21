import os

# Count lines in remaining_enbanc.txt
enbanc_file = "remaining_enbanc.txt"
if os.path.exists(enbanc_file):
    with open(enbanc_file, 'r') as f:
        enbanc_ids = [line.strip() for line in f if line.strip()]
    enbanc_count = len(enbanc_ids)
else:
    enbanc_count = 0
    enbanc_ids = []

print(f"Current En Banc targets: {enbanc_count}")

# Count turbo_relaunch files
turbo_files = [f"turbo_relaunch_{i:02d}.txt" for i in range(1, 51)]
turbo_ids = set()
for tf in turbo_files:
    if os.path.exists(tf):
        with open(tf, 'r') as f:
            for line in f:
                if line.strip():
                    turbo_ids.add(line.strip())

print(f"Turbo relaunch targets: {len(turbo_ids)}")

# Load the 1,264 significant cases
import psycopg2
import json
import re

report_path = r"C:\Users\rnlar\.gemini\antigravity\brain\e768aa86-6434-4f77-b82a-5c95636c43ba\significant_cases_refined_v3.md"
target_ids = []

if os.path.exists(report_path):
    with open(report_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip().startswith('|'): continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                try:
                    case_id = int(parts[1])
                    date_str = parts[2]
                    match = re.search(r'(\d{4})', date_str)
                    if match:
                        year = int(match.group(1))
                        if 1987 <= year <= 2025:
                            target_ids.append(case_id)
                except ValueError:
                    continue

def get_db_connection():
    db_connection_string = "postgresql://postgres:password@localhost:5432/sc_decisions"
    try:
        possible_paths = [
            'api/local.settings.json', 
            os.path.join(os.path.dirname(__file__), '../../api/local.settings.json'),
            '../../api/local.settings.json'
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    settings = json.load(f)
                    db_connection_string = settings['Values']['DB_CONNECTION_STRING']
                break
    except Exception:
        pass
    return psycopg2.connect(db_connection_string)

conn = get_db_connection()
cur = conn.cursor()

# Get significant cases with older Gemini models
target_models = ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-2.0-flash']
query = """
    SELECT id
    FROM sc_decided_cases 
    WHERE id IN %s AND ai_model IN %s
    ORDER BY id
"""
cur.execute(query, (tuple(target_ids), tuple(target_models)))
significant_ids = set(str(row[0]) for row in cur.fetchall())

print(f"Significant cases (older models): {len(significant_ids)}")

# Combine all targets
all_targets = set(enbanc_ids) | turbo_ids | significant_ids

print(f"\n=== PRIORITY CASES FLEET CALCULATION ===")
print(f"")
print(f"Current En Banc targets:          {enbanc_count:,}")
print(f"+ Turbo relaunch targets:         {len(turbo_ids):,}")
print(f"+ Significant cases (1987-2025):  {len(significant_ids):,}")
print(f"- Overlap (already included):     (calculating...)")

# Calculate overlap
overlap = (set(enbanc_ids) | turbo_ids) & significant_ids
print(f"- Overlap (already included):     {len(overlap):,}")
print(f"=" * 50)
print(f"TOTAL UNIQUE TARGETS:             {len(all_targets):,}")

# Export combined list
output_file = "priority_cases_fleet.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    for cid in sorted(all_targets, key=lambda x: int(x)):
        f.write(f"{cid}\n")

print(f"\n✓ Exported {len(all_targets):,} case IDs to {output_file}")

conn.close()
