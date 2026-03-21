import re

def normalize_roc(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove Amendment Resolutions and effective date notices
    # e.g., "2019 AMENDMENTS TO THE 1997 RULES OF CIVIL PROCEDURE"
    # e.g., "Resolution approving the 2019 Proposed Amendments..."
    content = re.sub(r'\*\*2019 AMENDMENTS TO THE.*?\*\*', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'Â Resolution approving the 2019 Proposed Amendments to the Revised Rules on Evidence.*?\n', '', content, flags=re.IGNORECASE)
    content = re.sub(r'Â', '', content) # Clean up remaining Â characters
    
    # 2. Header Centering and Normalization (Ensuring no double centering)
    # Rules of Court Title
    content = re.sub(r'^\s*\*\*RULES OF COURT\*\*\s*$', '<p align="center"># RULES OF COURT</p>', content, flags=re.MULTILINE)
    
    # Rule headers: ### RULE X\nTITLE
    def center_rules(match):
        rule_num = match.group(1)
        text_after = match.group(2).strip()
        lines = text_after.split('\n')
        title = ""
        remaining = ""
        if lines and lines[0].strip() and not lines[0].strip().startswith('#') and not lines[0].strip().startswith('Section') and not lines[0].strip().startswith('<p'):
            title = lines[0].strip()
            remaining = '\n'.join(lines[1:])
        
        if title:
            # Clean title of any existing formatting
            title = title.replace('**', '').strip()
            return f'\n<p align="center">### RULE {rule_num}<br>{title}</p>\n{remaining}'
        else:
            return f'\n<p align="center">### RULE {rule_num}</p>\n{text_after}'

    # Prevent matching if already centered
    content = re.sub(r'^(?!<p)### RULE\s+(\d+)(.*?)(?=\nSection|\n###|\n\*\*|$)', center_rules, content, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)

    # General Provisions (only if not already centered)
    content = re.sub(r'^(?<!<p align="center">)\s*GENERAL PROVISION[S]?\s*$', '<p align="center">### GENERAL PROVISIONS</p>', content, flags=re.MULTILINE | re.IGNORECASE)

    # Evidence Topics (A. ...)
    content = re.sub(r'^\s*\*\*([A-Z])\.\s*(.*?)\*\*\s*$', r'<p align="center">#### \1. \2</p>', content, flags=re.MULTILINE)
    
    # Evidence Sub-topics (1. ...)
    content = re.sub(r'^\s*\*\*(\d+)\.\s*(.*?)\*\*\s*$', r'<p align="center">##### \1. \2</p>', content, flags=re.MULTILINE)

    # 3. Footnote marker and Footer Cleanup (X X X)
    content = re.sub(r'^\s*X X X\s*$', '', content, flags=re.MULTILINE)
    
    # Remove empty <p align="center"> if any were created accidentally
    content = re.sub(r'<p align="center">\s*</p>', '', content)

    # 4. Section Header Normalization
    def normalize_section_header(match):
        sec_num = match.group(1)
        title = match.group(2).strip()
        sep = match.group(3)
        rest = match.group(4)
        title = title.replace('*', '').replace('_', '')
        return f'Section {sec_num}. *{title}*. {sep} {rest}'

    content = re.sub(r'^Section\s+(\d+)\.\s+(.*?)\.\s+([—–-])\s+(.*)', normalize_section_header, content, flags=re.MULTILINE)

    # 5. Cascading Indentation for Enumeration
    lines = content.split('\n')
    normalized_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            normalized_lines.append("")
            continue
            
        # Level 1: (a), (b), ...
        if re.match(r'^\([a-z]\)\s+', stripped):
            normalized_lines.append("    " + stripped)
        # Level 2: (1), (2), ... OR 1., 2.
        elif re.match(r'^(\(\d+\)|\d+\.)\s+', stripped) and not stripped.startswith('Section') and not stripped.startswith('RULE'):
            normalized_lines.append("        " + stripped)
        # Level 3: (i), (ii), ...
        elif re.match(r'^\([ivx]+\)\s+', stripped):
            normalized_lines.append("            " + stripped)
        else:
            normalized_lines.append(line)

    content = '\n'.join(normalized_lines)

    # Final cleanup of double blank lines and whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

if __name__ == "__main__":
    normalize_roc('ROC_Combined.md')
    print("Advanced normalization complete.")
