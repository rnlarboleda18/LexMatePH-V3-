import re
import os

file_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md\Quamto 2023 Civil Law_AI.md"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Diagnostic 1: How many units?
units = re.split(r'\n(?=Question\s*\()', content)
print(f"Total units found by split: {len(units)}")

# Diagnostic 2: Examine first few units
for i, unit in enumerate(units[:15]):
    unit_str = unit.strip()
    has_sa = "Suggested Answer" in unit
    q_len = len(unit)
    print(f"Unit {i}: Length={q_len}, Has 'Suggested Answer'={has_sa}")
    if i > 0 and not has_sa:
        print(f"--- FAILED UNIT {i} PREVIEW ---")
        print(unit[:200])
        print("---------------------------")

# Diagnostic 3: Check for "Suggested Answer" variations
all_sa = re.findall(r'Suggested Answer', content, re.IGNORECASE)
print(f"Total 'Suggested Answer' markers found: {len(all_sa)}")

# Diagnostic 4: Check if "Question (" is missing earlier?
all_q = re.findall(r'Question\s*\(', content, re.IGNORECASE)
print(f"Total 'Question (' markers found: {len(all_q)}")
