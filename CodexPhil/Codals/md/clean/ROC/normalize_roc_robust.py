import re

def normalize_roc_robust(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- STEP 1: RESET (Strip all previous structural formatting) ---
    # Strip HTML centering tags
    content = re.sub(r'<p align="center">', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</p>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
    
    # Strip Â and other artifacts
    content = content.replace('Â', '')
    
    # Strip extra whitespace and double rules left by previous runs
    content = re.sub(r'\n{3,}', '\n\n', content)

    # --- STEP 2: CLEANUP ---
    # Remove Amendment headers
    content = re.sub(r'(?i)\*\*2019 AMENDMENTS TO THE.*?\*\*', '', content)
    content = re.sub(r'(?i)Resolution approving the 2019 Proposed Amendments.*?\n', '', content)
    
    # Remove X X X markers
    content = re.sub(r'^\s*X X X\s*$', '', content, flags=re.MULTILINE)

    # --- STEP 3: APPLY CENTERING ---
    # Rules of Court Title
    content = re.sub(r'^Rules of Court$', '<p align="center"># RULES OF COURT</p>', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\s*\*\*RULES OF COURT\*\*\s*$', '<p align="center"># RULES OF COURT</p>', content, flags=re.MULTILINE | re.IGNORECASE)

    # Rule headers
    def center_rules(match):
        rule_num = match.group(1)
        text_after = match.group(2)
        
        # Split by lines and find the first non-empty line
        lines = text_after.split('\n')
        title = ""
        title_idx = -1
        
        for idx, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line:
                continue
            # If we hit a Section, stop
            if stripped_line.startswith('Section'):
                break
            
            # This looks like a title (ignore existing ### or ** or <p)
            title = stripped_line.replace('###', '').replace('**', '').replace('<p align="center">', '').replace('</p>', '').strip()
            title_idx = idx
            break
            
        if title:
            remaining = '\n'.join(lines[title_idx+1:])
            return f'\n<p align="center">### RULE {rule_num}<br>{title}</p>\n{remaining}'
        else:
            return f'\n<p align="center">### RULE {rule_num}</p>\n{text_after}'

    # More inclusive match for text_after
    content = re.sub(r'### RULE\s+(\d+)\s*\n(.*?)(?=\nSection|\n### RULE|$)', center_rules, content, flags=re.DOTALL | re.IGNORECASE)

    # General Provisions cleanup (robust)
    content = re.sub(r'^\s*<p align="center">### GENERAL PROVISIONS</p>\s*$', 'GENERAL PROVISIONS', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\s*### GENERAL PROVISIONS\s*$', 'GENERAL PROVISIONS', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^\s*GENERAL PROVISION[S]?\s*$', '<p align="center">### GENERAL PROVISIONS</p>', content, flags=re.MULTILINE | re.IGNORECASE)

    # Evidence Topics (A. ...)
    content = re.sub(r'^\s*\*\*([A-Z])\.\s*(.*?)\*\*\s*$', r'<p align="center">#### \1. \2</p>', content, flags=re.MULTILINE)
    
    # Evidence Sub-topics (1. ...)
    content = re.sub(r'^\s*\*\*(\d+)\.\s*(.*?)\*\*\s*$', r'<p align="center">##### \1. \2</p>', content, flags=re.MULTILINE)

    # --- STEP 4: SECTION NORMALIZATION ---
    def normalize_section_header(match):
        sec_num = match.group(1)
        title = match.group(2).strip()
        sep = match.group(3)
        rest = match.group(4)
        title = title.replace('*', '').replace('_', '')
        return f'Section {sec_num}. *{title}*. {sep} {rest}'

    # Match "Section X. Title. — "
    content = re.sub(r'^Section\s+(\d+)\.\s+(.*?)\.\s+([—–-])\s+(.*)', normalize_section_header, content, flags=re.MULTILINE)

    # --- STEP 5: CASCADING INDENTATION ---
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
        elif re.match(r'^(\(\d+\)|\d+\.)\s+', stripped) and not stripped.startswith('Section') and not stripped.startswith('RULE') and not stripped.startswith('RULE'):
            normalized_lines.append("        " + stripped)
        # Level 3: (i), (ii), ...
        elif re.match(r'^\([ivx]+\)\s+', stripped):
            normalized_lines.append("            " + stripped)
        else:
            normalized_lines.append(line)

    content = '\n'.join(normalized_lines)
    
    # Final cleanup
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

if __name__ == "__main__":
    normalize_roc_robust('ROC_Combined.md')
    print("Robust normalization complete.")
