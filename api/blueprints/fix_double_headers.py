import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()

# 1. Fix double header speaks near line 400
replaced_double = False
for i, line in enumerate(lines):
    if 'full_text = f"{header}.\\n\\n{clean}"' in line:
        print(f"Found target line at index {i}")
        lines[i] = """                # Deduplicate if Clean body already starts with the Header
                if header and clean.lower().startswith(header.lower().rstrip('.')):
                    header = ""
                full_text = f"{header}.\\n\\n{clean}" if header else clean"""
        replaced_double = True
        break

# 2. Increment Cache Version v20 to v21
replaced_cache = False
for i, line in enumerate(lines):
    if 'CACHE_VERSION = "v20"' in line:
        print(f"Found cache version line at index {i}")
        lines[i] = 'CACHE_VERSION = "v21" # Increment to force-refresh all cached audio'
        replaced_cache = True
        break

if replaced_double or replaced_cache:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Replace complete")
else:
    print("Mismatched target lines sequence")
