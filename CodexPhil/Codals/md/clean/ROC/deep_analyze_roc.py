import re

def analyze_structure(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    hierarchy = []
    multi_para_sections = []
    current_section = None
    current_section_lines = []

    for i, line in enumerate(lines):
        clean_line = line.strip()
        if not clean_line:
            continue

        # Detect headers
        if clean_line.startswith('#') or (clean_line.startswith('**') and clean_line.endswith('**')):
            hierarchy.append((i + 1, clean_line))
            current_section = None # Reset section tracking on any header
            continue

        # Detect Section starts
        section_match = re.match(r'^Section\s+(\d+)\.', clean_line, re.IGNORECASE)
        if section_match:
            if current_section:
                # Save previous section if it had multiple paragraphs
                if len(current_section_lines) > 1:
                    multi_para_sections.append(current_section_lines)
            
            current_section = section_match.group(1)
            current_section_lines = [(i + 1, clean_line)]
        elif current_section:
            # Check if this is a continuation paragraph or a list item
            # If it doesn't start with "### RULE" or another "Section", it's likely part of the same section
            # But we must exclude cases that look like new rules or major headers already handled
            current_section_lines.append((i + 1, clean_line))

    # Final check
    if current_section and len(current_section_lines) > 1:
        multi_para_sections.append(current_section_lines)

    print("--- Header Hierarchy (First 20) ---")
    for pos, h in hierarchy[:20]:
        print(f"L{pos}: {h}")

    print("\n--- Potential Multi-paragraph Sections (First 5) ---")
    for section in multi_para_sections[:5]:
        print(f"Section {section[0][1][:20]}... has {len(section)} non-empty lines.")
        for pos, line in section:
            print(f"  L{pos}: {line[:50]}...")
        print("-" * 10)

if __name__ == "__main__":
    analyze_structure('ROC_Combined.md')
