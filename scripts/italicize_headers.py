import os
import re

directory = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC"

def process_line(line):
    # Regex explicitly excludes lines with existing stars `*` in title
    # Supports "Section 1. ", "Sec. 2. ", "SECTION 3. ", with optional stars
    pattern = r'(Section \d+\.?|SECTION \d+\.?|Sec\. \d+\.?)\s+([^*.\-\–\—\-]+?)(\.?\s*[–\—\-]+)'
    
    def repl(m):
        prefix = m.group(1) # e.g. "Section 1."
        title = m.group(2)  # e.g. "Title of the Rules"
        suffix = m.group(3) # e.g. ". –"
        # Italicize title text
        return f"{prefix} *{title.strip()}*{suffix}"

    # Use iterate sub to avoid matching references lacking boundary dash
    return re.sub(pattern, repl, line)

count = 0
for filename in os.listdir(directory):
    if filename.endswith(".md"):
        path = os.path.join(directory, filename)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.readlines()
        
        new_content = [process_line(line) for line in content]
            
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_content)
        print(f"Processed Section Formatting: {filename}")
        count += 1

print(f"Successfully processed {count} files.")
