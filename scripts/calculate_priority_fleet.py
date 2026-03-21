import os

# Count lines in remaining_enbanc.txt
enbanc_file = "remaining_enbanc.txt"
if os.path.exists(enbanc_file):
    with open(enbanc_file, 'r') as f:
        enbanc_ids = set(line.strip() for line in f if line.strip())
else:
    enbanc_ids = set()

# Count turbo_relaunch files
turbo_files = [f"turbo_relaunch_{i:02d}.txt" for i in range(1, 51)]
turbo_ids = set()
for tf in turbo_files:
    if os.path.exists(tf):
        with open(tf, 'r') as f:
            turbo_ids.update(line.strip() for line in f if line.strip())

# Load the 1,264 significant cases from database
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
query = "SELECT id FROM sc_decided_cases WHERE id IN %s AND ai_model IN %s"
cur.execute(query, (tuple(target_ids), tuple(target_models)))
significant_ids = set(str(row[0]) for row in cur.fetchall())

print("=== PRIORITY CASES FLEET CALCULATION ===\n")
print(f"A. Remaining En Banc:              {len(enbanc_ids):,}")
print(f"B. Turbo Relaunch:                 {len(turbo_ids):,}")
print(f"C. Significant (1987-2025):        {len(significant_ids):,}")

# Calculate combinations and overlaps
existing_targets = enbanc_ids | turbo_ids
overlap_with_existing = significant_ids & existing_targets
new_from_significant = significant_ids - existing_targets

print(f"\nExisting targets (A ∪ B):          {len(existing_targets):,}")
print(f"Overlap (C ∩ (A ∪ B)):             {len(overlap_with_existing):,}")
print(f"New from significant (C - (A ∪ B)): {len(new_from_significant):,}")

all_targets = existing_targets | significant_ids

print(f"\n{'='*50}")
print(f"TOTAL PRIORITY CASES FLEET:        {len(all_targets):,}")
print(f"{'='*50}")

# Export - using simple approach
output_file = "priority_cases_fleet.txt"
try:
    sorted_ids = sorted([int(x) for x in all_targets])
    with open(output_file, 'w', encoding='utf-8') as f:
        for cid in sorted_ids:
            f.write(f"{cid}\n")
    print(f"\n✓ Exported {len(all_targets):,} case IDs to {output_file}")
except Exception as e:
    print(f"\n✗ Export failed: {e}")
    print(f"  Total remains: {len(all_targets):,} cases")

conn.close()
