filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
target = "prev_content.split('\\\\\\\\n\\\\\\\\n')"

replaced = False
for i, line in enumerate(lines):
    if "prev_content.split" in line and "\\\\n" in line:
        print(f"Found target line at index {i}: {line.strip()}")
        # Replace the literal split target with standard newline split
        lines[i] = line.replace("split('\\\\\\\\n\\\\\\\\n')", "split('\\n\\n')")
        replaced = True
        break

if replaced:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Replace complete")
else:
    print("Target line not found")
