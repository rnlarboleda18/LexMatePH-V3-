import re

def categorize_lowercase(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fragments = []
    list_items = []
    
    # Regex for list items: (a), a), 1., i., etc.
    list_regex = re.compile(r'^\s*(\(?[a-z0-9]+\)|[ivx]+\.)(\s+|$)', re.IGNORECASE)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Ignore headers, HTML, Section markers
        if stripped.startswith(('<', '#', 'RULE', 'GENERAL PROVISION', 'Section', '*', '_')):
            continue
            
        if stripped[0].islower():
            if list_regex.match(line):
                list_items.append((i + 1, stripped))
            else:
                fragments.append((i + 1, stripped))
                
    return fragments, list_items

if __name__ == "__main__":
    fragments, list_items = categorize_lowercase('ROC_Combined.md')
    print(f"FRAGMENTS: {len(fragments)}")
    print(f"LIST_ITEMS: {len(list_items)}")
    
    print("\n--- FRAGMENTS SAMPLE ---")
    for l, t in fragments[:10]:
        print(f"Line {l}: {t[:100]}...")
