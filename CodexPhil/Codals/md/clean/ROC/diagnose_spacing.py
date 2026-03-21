import re
import os

def find_spacing_issues(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Regex definitions for markers
    re_markers = [
        re.compile(r'^\s*(\([a-z]\)|[a-z][\)\.])\s+', re.IGNORECASE), # Level 1
        re.compile(r'^\s*(\(\d+\)|\d+[\)\.])\s+', re.IGNORECASE),      # Level 2
        re.compile(r'^\s*(\([ivx]+\)|[ivx]+[\)\.])\s+', re.IGNORECASE) # Level 3
    ]

    issues = []
    
    for i in range(len(lines)):
        line = lines[i]
        is_item = any(marker.match(line) for marker in re_markers)
        
        if is_item:
            # Check previous line
            if i > 0:
                prev_line = lines[i-1]
                if not prev_line.strip():
                    # It's an issue IF the line before that was also an item or part of an item
                    # OR if the user just wants NO space before ANY item.
                    issues.append({
                        'line_no': i + 1,
                        'type': 'blank line before item',
                        'content': line.strip(),
                        'prev_content': lines[i-1].strip() or "[EMPTY]"
                    })
            
            # Check next line
            if i < len(lines) - 1:
                next_line = lines[i+1]
                if not next_line.strip():
                    # Peek further to see if next content is also an item
                    for j in range(i+2, min(i+10, len(lines))):
                        if lines[j].strip():
                            if any(marker.match(lines[j]) for marker in re_markers):
                                issues.append({
                                    'line_no': i + 1,
                                    'type': 'blank line between items',
                                    'content': line.strip(),
                                    'next_item_line': j + 1,
                                    'next_item': lines[j].strip()
                                })
                            break
    return issues

if __name__ == "__main__":
    target = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC\ROC_Combined.md'
    print(f"Scanning {target} for spacing issues...")
    issues = find_spacing_issues(target)
    
    if not issues:
        print("No spacing issues found using the current logic.")
    else:
        print(f"Found {len(issues)} potential issues.")
        for issue in issues[:20]: # Show first 20
            print(issue)
