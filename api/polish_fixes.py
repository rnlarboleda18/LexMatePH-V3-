import re
import os

def polish_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
         content = f.read()
    
    # Fix 'text### RULE' -> 'text\n### RULE'
    # Match any character that is not a newline followed by '### RULE'
    # Use negative lookbehind or simple grouping
    cleaned = re.sub(r'([^\n])### RULE', r'\1\n### RULE', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
         f.write(cleaned)
    print(f"Polished spacing for: {file_path}")

def main():
    directory = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC'
    file1 = os.path.join(directory, '1. ROC Civil Procedure as amended 2019_fixed_chunked.md')
    if os.path.exists(file1):
         polish_file(file1)
    else:
         print(f"File not found: {file1}")

if __name__ == "__main__":
    main()
