import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()

# 1. Fix split '\\n\\n' to '\n\n'
target_split = "prev_content.split('\\n\\n')"
replaced_split = False
for i, line in enumerate(lines):
    if "prev_content.split" in line:
        print(f"Found split line at index {i}: {line.strip()}")
        # Replace '\\n\\n' with '\n\n'
        # The file contains literally: .split('\\n\\n')
        if "'\\n\\n'" in line:
             lines[i] = line.replace("'\\n\\n'", "'\\n\\n'") # wait, they were 4 backslashes in step 812
        # Use full match from Step 812: '\\\\n\\\\n'
        lines[i] = line.replace("'\\\\n\\\\n'", "'\\n\\n'")
        replaced_split = True
        break

# 2. Increment Cache Version v17 to v18
replaced_cache = False
for i, line in enumerate(lines):
    if 'CACHE_VERSION = "v17"' in line:
        print(f"Found cache version line at index {i}")
        lines[i] = 'CACHE_VERSION = "v18" # Increment to force-refresh all cached audio'
        replaced_cache = True
        break

if replaced_split or replaced_cache:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Replace complete")
else:
    print("Mismatched target lines sequence")
