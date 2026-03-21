import re

def extract_context(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    findings = []
    
    # regex for valid markers to ignore (same as before)
    ignore_regex = re.compile(r'^(\s*\(?[a-z0-9]+\)\s+|\s*\d+\.\s+)', re.IGNORECASE)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Skip headers, HTML, markers, and bold lines
        if stripped.startswith(('<', '#', 'RULE', 'GENERAL PROVISION', 'Section', '*', '_')):
            continue
            
        # Check if first character is lowercase
        if stripped[0].islower():
            # Check if it's a valid list marker to ignore
            if not ignore_regex.match(line):
                # Find preceding non-empty line
                prev_context = "None"
                for j in range(i-1, -1, -1):
                    if lines[j].strip():
                        prev_context = lines[j].strip()
                        break
                
                findings.append({
                    "line": i + 1,
                    "prev": prev_context,
                    "this": stripped
                })
                
    return findings

if __name__ == "__main__":
    results = extract_context('ROC_Combined.md')
    print(f"REPORT_START")
    for r in results:
        print(f"LINE: {r['line']}")
        print(f"PREV: {r['prev']}")
        print(f"THIS: {r['this']}")
        print("-" * 20)
    print(f"REPORT_END")
