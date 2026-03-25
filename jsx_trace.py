import re

def trace_balance(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    line_breaks = [0] + [m.start() + 1 for m in re.finditer(r'\n', content)]
    def get_line(pos):
        for i, start in enumerate(line_breaks):
            if pos < start:
                return i
        return len(line_breaks)

    content_clean = re.sub(r'\{/\*.*?\*/\}', '', content, flags=re.DOTALL)
    
    tag_pattern = re.compile(r'</?([a-zA-Z0-9_]+)(?:\s+[^>]*?)?>', re.DOTALL)
    
    stack = []
    
    print("--- STARTING TRACE ---")
    for match in tag_pattern.finditer(content_clean):
        full_tag = match.group(0)
        tag_name = match.group(1)
        pos = match.start()
        line_num = get_line(pos)

        if full_tag.endswith('/>') or tag_name.lower() in ['img', 'input', 'br', 'hr']:
            continue

        if full_tag.startswith('</'):
            if not stack:
                print(f"[{line_num}] Extra closing tag: </{tag_name}>")
                return
            top_tag, top_line = stack.pop()
            print(f"[{line_num}] Closed <{tag_name}> (opened at line {top_line})")
            if tag_name != top_tag:
                print(f"[{line_num}] Mismatch! </{tag_name}> vs <{top_tag}> from line {top_line}")
                return
        else:
            stack.append((tag_name, line_num))
            print(f"[{line_num}] Opened <{tag_name}>")

    print("--- END OF TRACE ---")
    if stack:
        print(f"Unclosed JSX tags at end of file:")
        for tag, l in stack:
            print(f"<{tag}> from line {l}")
    else:
        print("SUCCESS: All JSX tags balanced!")

if __name__ == '__main__':
    trace_balance(r"c:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\src\frontend\src\features\lexify\LexifyDashboard.jsx")
