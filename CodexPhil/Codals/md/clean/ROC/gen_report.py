import re

def generate_lowercase_report(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    report_lines = ["| Line | Previous Line Context | Lowercase Start Paragraph |", "| :--- | :--- | :--- |"]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Ignore indented lines (these are enumerations)
        if line.startswith(' '):
            continue
            
        # Ignore headers, HTML, and markers
        if stripped.startswith('<') or stripped.startswith('#') or re.match(r'^[\(\d\*\_]', stripped) or stripped.startswith('Section') or stripped.startswith('RULE'):
            continue
            
        # Check if first character is lowercase
        if stripped[0].islower():
            prev = lines[i-1].strip() if i > 0 else "[START]"
            if not prev:
                # Find the last non-empty line before this
                for j in range(i-1, -1, -1):
                    if lines[j].strip():
                        prev = lines[j].strip()
                        break
            
            report_lines.append(f"| {i+1} | {prev[:100]} | {stripped[:150]}... |")
            
    return "\n".join(report_lines)

if __name__ == "__main__":
    report = generate_lowercase_report('ROC_Combined.md')
    with open('lowercase_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print("Report generated in lowercase_report.txt")
