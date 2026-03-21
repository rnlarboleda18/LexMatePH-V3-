import os

file_path = "api/blueprints/codex.py"

with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
found = False
while i < len(lines):
    line = lines[i]
    if "mapped_rows.append({" in line and (i+2) < len(lines) and '"version_id"' in lines[i+1] and '"article_number"' in lines[i+2]:
        print(f"Match found at line {i+1}")
        new_lines.append(line)
        new_lines.append(lines[i+1])
        new_lines.append('                      "id": str(r[\'id\']),\n')
        new_lines.append('                      "key_id": str(r.get(\'article_num\') or ""),\n')
        new_lines.append(lines[i+2])
        i += 3
        found = True
    else:
        new_lines.append(line)
        i += 1

if found:
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    print("Migration successful")
else:
    print("Match NOT found with while loop")
