import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Match the exactly injected block
pattern = r"""(\s*if len\(last_seg\) < 45 and not last_seg\.upper\(\)\.startswith\('SECTION'\) and re\.match\(r'\^\[A-Za-z\]', last_seg\):\s*\n)\s*(header = f"\{last_seg\}\. \{header\}")"""

# Note the replacement inserts the conditional wrapper
replacement = r"""\1                                            if last_seg.lower() not in header.lower():\n                                                \2"""

content_new, count = re.subn(pattern, replacement, content)
print(f"Replaced {count} occurrences")

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
else:
    print("Failed to replace using regex, printing content chunk to analyze lines length offsets:")
    # print lines around 414
    lines = content.splitlines()
    for i in range(410, 422):
        print(f"{i+1}: {lines[i]}")
