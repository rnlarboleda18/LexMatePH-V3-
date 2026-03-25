import re

def check_jsx_balance(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create line starts map to compute line numbers accurately
    line_breaks = [0] + [m.start() + 1 for m in re.finditer(r'\n', content)]
    def get_line(pos):
        for i, start in enumerate(line_breaks):
            if pos < start:
                return i
        return len(line_breaks)

    # Strip inline comments: {/* ... */}
    content_clean = re.sub(r'\{/\*.*?\*/\}', '', content, flags=re.DOTALL)
    
    # Regex to extract tag names. Matches <tag or </tag with or without attributes
    tag_pattern = re.compile(r'</?([a-zA-Z0-9_]+)(?:\s+[^>]*?)?>', re.DOTALL)
    
    stack = []
    
    for match in tag_pattern.finditer(content_clean):
        full_tag = match.group(0)
        tag_name = match.group(1)
        pos = match.start()
        line_num = get_line(pos)

        # Skip self-closing tags: <tag /> or void tags
        if full_tag.endswith('/>') or tag_name.lower() in ['img', 'input', 'br', 'hr']:
            continue

        if full_tag.startswith('</'):
            if not stack:
                print(f"Extra closing tag '</{tag_name}>' at line {line_num}")
                return
            top_tag, top_line = stack.pop()
            if tag_name != top_tag:
                print(f"Mismatched tag '</{tag_name}>' at line {line_num}. Expected closing for '<{top_tag}>' from line {top_line}")
                return
        else:
            stack.append((tag_name, line_num))

    if stack:
        print(f"Unclosed JSX tags left:")
        for tag, l in stack:
            print(f"<{tag}> from line {l}")
    else:
        print("SUCCESS: All JSX tags balanced!")

if __name__ == '__main__':
    check_jsx_balance(r"c:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\src\frontend\src\features\lexify\LexifyDashboard.jsx")
