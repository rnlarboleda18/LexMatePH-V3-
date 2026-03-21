import re

def scan_with_sections(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_section = "None"
    findings = []
    
    # Ignore patterns: (a), (1), i., 1., etc.
    ignore_regex = re.compile(r'^(\s*\(?[a-z0-9]+\)\s+|\s*\d+\.\s+|\s*[ivx]+\.\s+)', re.IGNORECASE)

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
            # Check if it's a valid list marker we should ignore
            if not ignore_regex.match(line):
                findings.append({
                    "line": i + 1,
                    "section": current_section,
                    "text": stripped
                })
                
    return findings

if __name__ == "__main__":
    results = scan_with_sections('ROC_Combined.md')
    print(f"Total found: {len(results)}")
    for r in results:
        print(f"Line {r['line']} | {r['section']} | {r['text'][:60]}...")
