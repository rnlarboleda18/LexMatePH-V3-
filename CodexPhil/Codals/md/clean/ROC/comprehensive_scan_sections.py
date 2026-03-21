import re

def comprehensive_scan_sections(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_section = "None"
    findings = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Update current section
        section_match = re.search(r'^Section\s+(\d+)\.\s*(.*?)[\.—]', stripped)
        if section_match:
            current_section = f"Section {section_match.group(1)} ({section_match.group(2).strip()})"
        
        # Skip headers, HTML, and markers
        if stripped.startswith(('<', '#', 'RULE', 'GENERAL PROVISION')) or stripped.startswith('Section'):
            continue
        
        # Check for lowercase start
        if stripped[0].islower():
            findings.append({
                "line": i + 1,
                "section": current_section,
                "text": stripped
            })
                
    return findings

if __name__ == "__main__":
    results = comprehensive_scan_sections('ROC_Combined.md')
    print(f"Total found: {len(results)}")
    for r in results:
        print(f"Line {r['line']} | {r['section']} | {r['text'][:100]}")
