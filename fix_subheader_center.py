import re

file_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\components\ArticleNode.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Target: <p {...props} className="whitespace-pre-wrap !m-0 text-justify" style={{ maxWidth: "none" }}>
pattern = r'(<p\s+\{\.\.\.props\}\s+className="whitespace-pre-wrap\s+!m-0\s+text-justify"\s+style=\{\{\s*maxWidth:\s*"none"\s*\}\}>)'

# Replace with conditional className
replacement = r'<p {...props} className={`whitespace-pre-wrap !m-0 ${isSubHeader ? "text-center font-bold text-amber-800 dark:text-amber-400 uppercase tracking-wide" : "text-justify"}`} style={{ maxWidth: "none" }}>'

new_content = re.sub(pattern, replacement, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replacement complete.")
print("Matches:", len(re.findall(pattern, content)))
