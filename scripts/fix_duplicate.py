
path = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\SupremeDecisions.jsx"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines are 0-indexed in list, but my view was 1-indexed.
# I want to remove 1130 to 1168 (inclusive).
# So indices 1129 to 1168.

start_idx = 1129
end_idx = 1168

# Verify content before deleting
print(f"Deleting lines {start_idx+1} to {end_idx+1}:")
print(lines[start_idx].strip())
print("...")
print(lines[end_idx-1].strip()) # 1168th line is index 1167 check inside

# Slice out the lines
new_lines = lines[:start_idx] + lines[end_idx:]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Done.")
