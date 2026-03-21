import re

def analyze_lowercase_starts(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    findings = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Ignore indented lines (already handled by normalization)
        if line.startswith(' '):
            continue
            
        # Ignore headers and HTML
        if stripped.startswith('<') or stripped.startswith('#'):
            continue
            
        # Ignore lines starting with enumeration markers or bold/italics
        if re.match(r'^[\(\d\*\_]', stripped):
            continue
            
        # Check if first character is lowercase
        if stripped[0].islower():
            # Get context: 1 line before and current line
            prev_line = lines[i-1].strip() if i > 0 else "[START OF FILE]"
            findings.append({
                "line_number": i + 1,
                "prev_line": prev_line,
                "current_line": stripped
            })
            
    return findings

if __name__ == "__main__":
    findings = analyze_lowercase_starts('ROC_Combined.md')
    if findings:
        print(f"REPORT: Found {len(findings)} lowercase starts.")
        for f in findings:
            print(f"--- Line {f['line_number']} ---")
            print(f"PREV: {f['prev_line'][:80]}")
            print(f"THIS: {f['current_line'][:120]}")
    else:
        print("No lowercase starts found after filtering.")
