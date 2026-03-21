filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\blueprints\audio_provider.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()

# 1. Revert cols assignment (approx line 316)
for i, line in enumerate(lines[:350]):
    if 'cols = "article_num, article_title, group_header, content_md, list_order, article_label"' in line:
        print(f"Found cols line at index {i}")
        lines[i] = '                cols = "article_num, article_title, group_header, content_md"'
        break

# 2. Revert Header Title limiter and Injected block
# Find line 391 approx
new_lines = []
skip = False
for i, line in enumerate(lines):
    if "# For Constitution, only include main Article Title on Start items" in line:
        # We start skip or replace
        # Replace up to line 398 which is next empty space
        # But wait, we need to KEEP header += f'. {art_title}'
        new_lines.append("                    header += f'. {art_title}'")
        skip = True
        continue
    
    if skip and "header += f'. {art_title}'" in line:
        # End skip for the first limiter section
        skip = False
        continue
        
    if "# Prepend Contextual Headers for Constitution Start Items" in line:
        # Start skip for the full peek block layout
        skip = True
        continue
        
    if skip and "# Apply custom pronunciations" in line:
        # End skip
        skip = False
        # Fall through to add this line
        
    if not skip:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Revert complete")
