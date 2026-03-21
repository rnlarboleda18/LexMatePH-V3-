import re

def find_lowercase_paragraphs(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    problems = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Skip headers (start with < or #)
        if stripped.startswith('<') or stripped.startswith('#'):
            continue
            
        # Check if it's a paragraph (not starting with Section, Rule, or enumeration)
        # We want to catch lines starting with lowercase a-z
        # but NOT catching (a), (b) etc which are indented or start with (
        if re.match(r'^[a-z]', stripped):
            problems.append((i + 1, stripped))
            
    return problems

if __name__ == "__main__":
    results = find_lowercase_paragraphs('ROC_Combined.md')
    if results:
        print(f"Found {len(results)} potential lowercase starts:")
        for line_num, text in results[:20]: # Show first 20
            print(f"Line {line_num}: {text[:100]}...")
    else:
        print("No lowercase starts found.")
