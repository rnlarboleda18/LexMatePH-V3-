import sys

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize newlines
content = content.replace('\r\n', '\n')

target = 'const isLastSegment = segIdx === segments.length - 1;'
replacement = 'const isLastSegment = segIdx === lastSubstantiveIdx;'

if target in content:
    content_new = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    print("Target not found")
