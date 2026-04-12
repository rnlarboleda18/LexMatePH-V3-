import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Match the hallucinatory line 526
target1 = r'className="inline-flex items-center gap-1 absolute right-0 top-0 ml-4 cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors align-baseline"'

# 2. Match standard line 558
target2 = r'className="inline-flex items-center gap-1 ml-1 cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors align-baseline"'

# Replacement rule: add ml-3, px-1, and bg badge rounded aesthetic
replacement = 'className="inline-flex items-center gap-1 ml-3 px-1.5 py-0.5 bg-indigo-50 dark:bg-indigo-900/40 rounded-md cursor-pointer text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 shadow-sm transition-colors align-baseline"'

content_new = content.replace(target1, replacement)
count1 = 1 if content_new != content else 0

content_new2 = content_new.replace(target2, replacement)
count2 = 1 if content_new2 != content_new else 0

print(f"Replaced target1: {count1}, target2: {count2}")

if count1 > 0 or count2 > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new2)
    print("Replace complete")
else:
    print("No targets matched")
