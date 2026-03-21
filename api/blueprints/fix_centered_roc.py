import re

filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Match exact <p> return stream with braces
target_regex = r'<p\s+\{\.\.\.props\}\s+className="!m-0\s+whitespace-pre-wrap"\s+style=\{\{\s*paddingLeft:\s*`\$\{finalPadding\}rem`,\s*textIndent:\s*finalIndent,\s*maxWidth:\s*"none"\s*\}\}\s*>'

replacement = '<p {...props} className={`!m-0 whitespace-pre-wrap ${isSubHeader ? "text-center font-bold text-gray-900 dark:text-gray-200 uppercase tracking-wide text-[20px]" : ""}`} style={{ paddingLeft: isSubHeader ? "0" : `${finalPadding}rem`, textIndent: isSubHeader ? "0" : finalIndent, maxWidth: "none" }}>'

content_new, count = re.subn(target_regex, replacement, content)

print(f"Replaced {count} occurrences")

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("Replace complete")
else:
    print("Mismatched target regexes bounds")
