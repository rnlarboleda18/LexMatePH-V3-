import re

def comprehensive_lowercase_scan(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    all_findings = []
    
    # regex for valid markers to ignore:
    # (a), (b), (1), (2), 1., 2., i., ii., (i), (ii)
    # also #, <, Section, RULE
    markers_to_ignore = [
        r'^\s*\(?[a-z]\)\s+',        # (a) or a)
        r'^\s*\(?\d+\)\s+',          # (1) or 1)
        r'^\s*\d+\.\s+',             # 1.
        r'^\s*\(?[ivx]+\)\s+',       # (i) or i)
        r'^\s*[ivx]+\.\s+',          # i.
        r'^\s*#',                    # Markdown headers
        r'^\s*<',                    # HTML tags
        r'^\s*Section',              # Section headers
        r'^\s*### RULE',             # Rule headers
        r'^\s*GENERAL PROVISION',     # Specific headers
        r'^\s*\*\*',                 # Bold markers
        r'^\s*Â',                    # Any odd artifacts
        r'^\s*$'                     # Empty lines
    ]
    
    ignore_regex = re.compile('|'.join(markers_to_ignore), re.IGNORECASE)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # If it doesn't match the ignore list, check if the first available char is lowercase
        if not ignore_regex.match(line):
            # Check the first alpha character
            first_alpha = re.search(r'[a-zA-Z]', stripped)
            if first_alpha and first_alpha.group().islower():
                # Potential lowercase start
                all_findings.append({
                    "line_number": i + 1,
                    "text": stripped
                })
                
    return all_findings

if __name__ == "__main__":
    findings = comprehensive_lowercase_scan('ROC_Combined.md')
    print(f"TOTAL_FOUND: {len(findings)}")
    for f in findings:
        print(f"{f['line_number']}: {f['text'][:100]}")
