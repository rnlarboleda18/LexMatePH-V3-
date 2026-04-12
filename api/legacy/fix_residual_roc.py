import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Match the isRocArticle line in ul/ol blocks
# Use spacing-agnostic regex
target_regex = r"const\s+isRocArticle\s*=\s*\(codeId\s*&&\s*String\(codeId\)\.toLowerCase\(\)\s*===\s*'roc'\)\s*\|\|\s*\(article\s*&&\s*article\.code_id\s*&&\s*String\(article\.code_id\)\.toLowerCase\(\)\s*===\s*'roc'\);"

replacement = "const isRocArticle = (codeId && ['roc', 'rpc'].includes(String(codeId).toLowerCase())) || (article && article.code_id && ['roc', 'rpc'].includes(String(article.code_id).toLowerCase()));"

content_new, count = re.subn(target_regex, replacement, content)

print(f"Replaced {count} occurrences")

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    print("Mismatched target regexes bounds")
