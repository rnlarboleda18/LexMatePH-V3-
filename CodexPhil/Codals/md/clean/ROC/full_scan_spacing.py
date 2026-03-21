import re
import os

def check_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    re_marker = re.compile(r'^\s*(\([a-z]\)|[a-z][\)\.]|\(\d+\)|\d+[\)\.]|\([ivx]+\)|[ivx]+[\)\.])\s+', re.IGNORECASE)
    
    issues = 0
    for i in range(1, len(lines)):
        if re_marker.match(lines[i]):
            if not lines[i-1].strip():
                # Potential issue: blank line before a marker
                # But we need to know if the line BEFORE that was also an item or part of the same section.
                # Actually, the user wants NO space between items.
                # So if i-2 was also part of an item or a marker...
                # Let's just find ALL instances where an item has a blank line before it.
                issues += 1
                if issues < 10:
                    print(f"  Line {i+1}: {lines[i].strip()} (Preceded by blank line)")
    return issues

if __name__ == "__main__":
    directory = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC'
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            path = os.path.join(directory, filename)
            print(f"Checking {filename}...")
            count = check_file(path)
            print(f"  Found {count} instances.")
