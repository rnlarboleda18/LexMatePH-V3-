import sys
import re

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

# Setup fake row 4 simulating DB output
row = {
    'id': 4,
    'article_num': 'II',
    'article_label': 'ARTICLE II',
    'article_title': 'Declaration of Principles and State Policies',
    'section_label': 'SECTION 1.',
    'group_header': None,
    'content_md': 'SECTION 1. The Philippines is a democratic and republican State.\nSovereignty resides in the people and all government authority emanates\nfrom them.',
    'list_order': 4
}

# Simulate cleaning logic in audio_provider.py
content = (row.get('content_md') or '').strip()
clean = re.sub(r'[#*`_\[\]]', ' ', str(content))
clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

# Simulate Header format
art_num = str(row.get('article_num') or '')
art_title = (row.get('article_title') or '').strip()

clean_num = art_num
# Line 387: if '-' in art_num and not art_num[0].isdigit(): ...
# In this case no '-' present.
is_redundant = False # Simulate

header = 'Preliminary Article' if clean_num == '0' else f'Article {clean_num}'
if art_title and not is_redundant: 
    header += f'. {art_title}'

# Apply new injection logic
code_id = 'const'
table = 'consti_codal'

if code_id and code_id.lower() == 'const':
    label = row.get('article_label') or ''
    # clean_num is "II"
    if clean_num == '1' or clean_num == '0' or "PREAMBLE" in clean_num.upper():
        if label and art_title:
             header = f"{label} {art_title}. {header}"

print(f"Header: '{header}'")
print(f"Clean: '{clean}'")

full_text = f"{header}.\n\n{clean}"
print(f"\n--- FULL TEXT ---")
print(full_text)
