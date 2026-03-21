import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()

# 1. Fix single newlines inside paragraph content
replaced_pause = False
for i, line in enumerate(lines):
    if "clean = re.sub(r'\\n{3,}', '\\n\\n', clean).strip()" in line:
        print(f"Found target line at index {i}")
        # Insert SINGLE newline replacement BELOW line 382
        lines[i] = """                clean = re.sub(r'\\n{3,}', '\\n\\n', clean).strip()
                # Replace single newlines with spaces to prevent artificial pauses inside sentences
                clean = re.sub(r'(?<!\\n)\\n(?!\\n)', ' ', clean)"""
        replaced_pause = True
        break

# 2. Increment Cache Version v23 to v24
replaced_cache = False
for i, line in enumerate(lines):
    if 'CACHE_VERSION = "v23"' in line:
        print(f"Found cache version line at index {i}")
        lines[i] = 'CACHE_VERSION = "v24" # Increment to force-refresh all cached audio'
        replaced_cache = True
        break

if replaced_pause or replaced_cache:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Replace complete")
else:
    print("Mismatched target lines sequence")
