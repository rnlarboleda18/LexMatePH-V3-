import psycopg2
import json
import os
import re
from collections import Counter

# Load significant cases from MD file
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

print(f"Total significant cases (1987-2025): {len(target_ids)}")

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

if not target_ids:
    print("No cases found.")
    exit()

conn = get_db_connection()
cur = conn.cursor()

# Get cases with older Gemini models
target_models = ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-2.0-flash']
query = """
    SELECT id, ai_model, division, date, short_title 
    FROM sc_decided_cases 
    WHERE id IN %s AND ai_model IN %s
    ORDER BY id
"""
cur.execute(query, (tuple(target_ids), tuple(target_models)))
results = cur.fetchall()

print(f"\n=== PRIORITY CASES FLEET CALCULATION ===\n")
print(f"Starting pool: {len(target_ids)} significant cases (1987-2025)")
print(f"Filtered to older Gemini models: {len(results)} cases")

# Breakdown by model
model_counts = Counter()
for cid, model, division, date, title in results:
    model_counts[model] += 1

print(f"\n--- By Model ---")
for model, count in sorted(model_counts.items()):
    print(f"  {model}: {count}")

# Breakdown by division
division_counts = Counter()
enbanc_count = 0
for cid, model, division, date, title in results:
    division_counts[division] += 1
    if division and 'banc' in division.lower():
        enbanc_count += 1

print(f"\n--- By Division ---")
print(f"  En Banc: {enbanc_count}")
print(f"  Division cases: {len(results) - enbanc_count}")

print(f"\n=== PRIORITY CASES FLEET TARGET ===")
print(f"Total cases for redigestion: {len(results)}")
print(f"\nCalculation:")
print(f"  Significant cases (1987-2025) = {len(target_ids)}")
print(f"  Cases with older Gemini models = {len(results)}")
print(f"  Cases with newer models (excluded) = {len(target_ids) - len(results)}")

# Export IDs
output_file = "priority_cases_fleet_targets.txt"
with open(output_file, 'w') as f:
    for cid, model, division, date, title in results:
        f.write(f"{cid}\n")

print(f"\n✓ Exported {len(results)} case IDs to {output_file}")

conn.close()
