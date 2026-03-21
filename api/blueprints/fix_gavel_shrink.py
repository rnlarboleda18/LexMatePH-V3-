import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Match the Gavel icons with className="inline" inside `<span className="inline-flex ...">`
# There are two of them near lines 534 and 565 approx.
target = r'<Gavel size={14} className="inline" />'
replacement = r'<Gavel size={14} className="flex-shrink-0" />'

content_new = content.replace(target, replacement)
count = content.count(target) - content_new.count(target)

print(f"Replaced {count} instances of target")

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    print("No targets matched")
