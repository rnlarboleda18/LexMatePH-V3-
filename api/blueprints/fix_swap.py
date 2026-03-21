import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Match the exactly injected block with deduplication from last step
pattern = r"""(\s*if len\(last_seg\) < 45 and not last_seg\.upper\(\)\.startswith\('SECTION'\) and re\.match\(r'\^\[A-Za-z\]', last_seg\):\s*\n)\s*if last_seg\.lower\(\) not in header\.lower\(\):\s*\n\s*header = f"\{last_seg\}\. \{header\}" """

replacement = r"""\1                                            # Append after main header instead of prepending\n                                            header = f"{header}. {last_seg}" """

# To avoid regex whitespace failures, simply do a lines replace if exact line string is found:
lines = content.splitlines()
target_block_start = "if len(last_seg) < 45 and not last_seg.upper().startswith('SECTION') and re.match(r'^[A-Za-z]', last_seg):"

replaced = False
for i, line in enumerate(lines):
    if target_block_start in line:
        # We found the block! Modifying lines i+1 and i+2
        # Deduplication check must be at i+1
        if "if last_seg.lower() not in header.lower():" in lines[i+1]:
            print(f"Found target block at line {i+1}")
            # Replace next 2 lines with append logic
            lines[i+1] = "                                            # Append after main header instead of prepending"
            lines[i+2] = '                                            header = f"{header}. {last_seg}"'
            replaced = True
            break

if replaced:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Replace complete")
else:
    print("Mismatched target lines sequence")
    for i in range(414, 422):
        print(f"{i+1}: {lines[i]}")
