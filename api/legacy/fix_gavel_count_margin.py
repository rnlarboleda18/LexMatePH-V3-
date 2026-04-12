import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Match count span inside the Gavel badge tag
target = r'<span className="text-xs font-semibold">{linkCount}</span>'
replacement = r'<span className="text-xs font-semibold ml-1">{linkCount}</span>'

content_new = content.replace(target, replacement)
count = content.count(target) - content_new.count(target)

print(f"Replaced {count} instances of target")

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    print("No targets matched")
