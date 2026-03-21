import re

def find_indentation_targets(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by Section to analyze each independently
    sections = re.split(r'(?i)(Section\s+\d+\.)', content)
    
    targets = []
    
    # sections[0] is everything before first Section
    for i in range(1, len(sections), 2):
        header = sections[i]
        body = sections[i+1] if i+1 < len(sections) else ""
        
        # Look for (a), (b) or 1., 2. patterns in the body
        has_alpha = re.search(r'\n\([a-z]\)\s+', body)
        has_numeric = re.search(r'\n\d+\.\s+', body)
        has_roman = re.search(r'\n\([ivx]+\)\s+', body)
        
        if has_alpha or has_numeric or has_roman:
            targets.append({
                'header': header.strip(),
                'sample': body.strip()[:100].replace('\n', ' '),
                'types': [t for t, found in [('alpha', has_alpha), ('numeric', has_numeric), ('roman', has_roman)] if found]
            })

    print(f"Total Sections with enumeration: {len(targets)}\n")
    print("--- Top Targets for Cascading Indentation ---")
    for t in targets[:20]:
        print(f"[{t['header']}] Types: {', '.join(t['types'])}")
        print(f"  Sample: {t['sample']}...")
        print("-" * 15)

if __name__ == "__main__":
    find_indentation_targets('ROC_Combined.md')
