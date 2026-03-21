import re

file_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Standard paragraphs: add style={{ maxWidth: 'none' }}
pattern1 = r'(<p \{\.\.\.props\} className="whitespace-pre-wrap !m-0 text-justify")'
replace1 = r'\1 style={{ maxWidth: "none" }}'

# 2. ROC paragraphs: add maxWidth: "none" into existing style object
pattern2 = r'style=\{\{\s*paddingLeft:\s*`\$\{finalPadding\}rem`,\s*textIndent:\s*finalIndent\s*\}\}'
replace2 = r'style={{ paddingLeft: `${finalPadding}rem`, textIndent: finalIndent, maxWidth: "none" }}'

new_content = re.sub(pattern1, replace1, content)
new_content = re.sub(pattern2, replace2, new_content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replacement complete.")
print("Matches 1:", len(re.findall(pattern1, content)))
print("Matches 2:", len(re.findall(pattern2, content)))
