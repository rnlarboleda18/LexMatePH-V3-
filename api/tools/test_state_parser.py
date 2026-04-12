import re
import os

def test_parse(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sections = []
    current_rule = None
    current_rule_title = None
    
    active_section = None
    pending_headers = []
    
    # Regexes
    rule_pattern = re.compile(r'^###\s+RULE\s+(\d+)(.*)', re.IGNORECASE)
    section_pattern = re.compile(r'^Section\s+(\d+)\.(.*)', re.IGNORECASE)
    
    # Sub-headers match
    subheader_pattern1 = re.compile(r'^##\s+(.*)') # e.g. ## A. OBJECT...
    subheader_pattern2 = re.compile(r'^###\s+(?!RULE)(.*)') # e.g. ### 1. Original... 
    # List style header: Floating titles like "1. Qualification of Witnesses"
    # To prevent grabbing section list items, we require it to be short or Title Case
    # Often, section list items have trailing text. Floating titles are standalone.
    list_header_pattern = re.compile(r'^\d+\.\s+[A-Z][a-zA-Z\s,\[\]\(\)]+$') # Standalone item

    def flush_section():
        nonlocal active_section
        if active_section:
            sections.append(active_section)
            active_section = None

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            if active_section:
                active_section['content_lines'].append("")
            continue

        # 1. Match Rule
        rule_match = rule_pattern.match(line_stripped)
        if rule_match:
            flush_section()
            current_rule = rule_match.group(1).strip()
            title_part = rule_match.group(2).strip()
            current_rule_title = title_part if title_part else ""
            continue

        # 2. Match Section
        sec_match = section_pattern.match(line_stripped)
        if sec_match:
            flush_section()
            sec_num = sec_match.group(1).strip()
            rest = sec_match.group(2).strip()
            
            title_match = re.search(r'\*(.*?)\*', rest)
            sec_title = title_match.group(1).strip() if title_match else ""
            
            content = rest
            if title_match:
                content = rest.replace(f'*{sec_title}*', '').strip()
                content = re.sub(r'^[.\s\-_—–]+', '', content).strip()

            content_lines = []
            # Prepend nested headers before section content
            if pending_headers:
                for h in pending_headers:
                    content_lines.append(h)
                    content_lines.append("") # space
                pending_headers = [] # Reset

            content_lines.append(content)

            active_section = {
                'rule_num': current_rule,
                'rule_title': current_rule_title,
                'section_num': sec_num,
                'section_title': sec_title,
                'content_lines': content_lines
            }
            continue

        # 3. Match Floating Sub-headers (Check BEFORE active_section to avoid swallowing)
        is_subheader = False
        if subheader_pattern1.match(line_stripped):
             is_subheader = True
        elif subheader_pattern2.match(line_stripped) and not line_stripped.startswith('### RULE'):
             is_subheader = True

        if is_subheader:
             with open('api/headers_log.txt', 'a', encoding='utf-8') as f:
                 f.write(f"Line {i+1} SUBHEADER: {line_stripped}\n")
             flush_section() # Close previous section so it doesn't swallow this header
             pending_headers.append(line_stripped)
             continue

        # List Header Pattern: 1. Qualification of Witnesses
        # Make sure not to steal list items from inside sections using length heuristic
        if list_header_pattern.match(line_stripped) and len(line_stripped) < 40:
             with open('api/headers_log.txt', 'a', encoding='utf-8') as f:
                 f.write(f"Line {i+1} LIST_HEADER: {line_stripped}\n")
             flush_section() # Standalone header
             pending_headers.append(line_stripped)
             continue

        # 4. Append to active section content
        if active_section:
             active_section['content_lines'].append(line_stripped)

    # Flush last
    flush_section()
    return sections

def main():
    filepath = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC\4. ROC Evidence as amended 2019.md'
    # Clear log
    if os.path.exists('api/headers_log.txt'):
         os.remove('api/headers_log.txt')
         
    sections = test_parse(filepath)
    print(f"Total sections: {len(sections)}")
    
    with open('api/test_output.txt', 'w', encoding='utf-8') as f:
        for sec in sections:
            if sec['rule_num'] == '130' and sec['section_num'] == '3':
                f.write("--- Section 3 Rule 130 content ---\n")
                for l in sec['content_lines']:
                    f.write(l + "\n")
    print("Wrote to api/test_output.txt")

if __name__ == "__main__":
    main()
