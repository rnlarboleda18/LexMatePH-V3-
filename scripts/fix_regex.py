
path = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\SupremeDecisions.jsx"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Match the problematic line containing: const boldMatch = cleanLine.match(/^(\*\*|*)([^\*]+)(\*\*|*)\s*(.*)/);
    if "const boldMatch = cleanLine.match(/^(\*\*|*)([^\*]+)" in line:
        print("Found line:", line.strip())
        # Replace with a safe comment or updated logic
        new_lines.append("                // regex removed removed to fix build error. Using colonMatch logic below.\n")
    else:
        new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Finished processing.")
