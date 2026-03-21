
import re
import os

path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\sc_elib_html (missing from lawphil)\70041.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

markers = {
    'SO ORDERED': [m.start() for m in re.finditer('SO ORDERED', content)],
    'CONCURRING AND DISSENTING OPINION': [m.start() for m in re.finditer('CONCURRING AND DISSENTING OPINION', content)],
    'LEONEN': [m.start() for m in re.finditer('LEONEN', content)],
    'HR DIVIDER': [m.start() for m in re.finditer('<hr', content)],
    'FOOTNOTE [1]': [m.start() for m in re.finditer(r'\[1\]', content)],
    'FOOTNOTE [50]': [m.start() for m in re.finditer(r'\[50\]', content)],
    'FOOTNOTE [80]': [m.start() for m in re.finditer(r'\[80\]', content)],
    'FOOTNOTE [100]': [m.start() for m in re.finditer(r'\[100\]', content)],
}

# Sort all markers by position
all_found = []
for label, positions in markers.items():
    for pos in positions:
        all_found.append((pos, label))

all_found.sort()

for pos, label in all_found:
    context = content[pos:pos+50].replace('\n', ' ')
    print(f'{pos}: {label} -> {context}')
