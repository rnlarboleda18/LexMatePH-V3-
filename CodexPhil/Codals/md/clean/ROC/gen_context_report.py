import re

def generate_full_context_report(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_section = "None"
    ignore_regex = re.compile(r'^(\s*\(?[a-z0-9]+\)\s+|\s*\d+\.\s+)', re.IGNORECASE)
    
    report = ["# Comprehensive Lowercase Start Report with Context\n",
              "| Line | Parent Section | Preceding Line (Context) | Lowercase Paragraph Start |",
              "| :--- | :--- | :--- | :--- |"]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Update current section
        section_match = re.search(r'^Section\s+(\d+)\.\s*(.*?)[\.—]', stripped)
        if section_match:
            current_section = f"Section {section_match.group(1)} ({section_match.group(2).strip()})"
        
        # Skip headers, HTML, and markers
        if stripped.startswith(('<', '#', 'RULE', 'GENERAL PROVISION', 'Section', '*', '_')):
            continue
        
        if stripped[0].islower() and not ignore_regex.match(line):
            # Find preceding non-empty line
            prev = "None"
            for j in range(i-1, -1, -1):
                if lines[j].strip():
                    prev = lines[j].strip()
                    break
            
            # Escape pipes for markdown table
            prev_esc = prev.replace('|', '\\|')
            this_esc = stripped.replace('|', '\\|')
            
            report.append(f"| {i+1} | {current_section} | {prev_esc[:100]} | {this_esc[:100]}... |")
            
    return "\n".join(report)

if __name__ == "__main__":
    report_content = generate_full_context_report('ROC_Combined.md')
    with open('C:/Users/rnlar/.gemini/antigravity/brain/23987f6c-77ad-4a99-beca-66dd66648985/lowercase_context_report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    print("Full context report generated.")
