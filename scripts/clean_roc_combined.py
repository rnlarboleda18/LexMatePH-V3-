import re
import os

def clean_markdown(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    
    # Patterns to catch redundant headers/footers
    header_patterns = [
        r'^ROC Civil Procedure as amended 2019$',
        r'^ROC Special Proceeding$',
        r'^ROC Criminal Procedure$',
        r'^ROC Evidence as amended 2019$',
        r'^\*\*RULES OF COURT\*\*',
        r'^RULES OF COURT$',
        r'^\*\*2019 AMENDMENTS TO THE.*RULES OF CIVIL PROCEDURE.*\*\*¹',
        r'^\*\*2019 AMENDMENTS TO THE .*RULES ON EVIDENCE.*\*\*',
        r'^PROCEDURE IN REGIONAL TRIAL COURTS$',
        r'^\s*\d+\s*$', # Page numbers
        r'^Page \d+$',
        r'^---+$', # Horizontal rules between pages if they are alone
    ]
    
    # Pass 1: Basic cleaning (headers/footers, rule duplicates, bracket removal, bleed-in fixes)
    pass1_lines = []
    last_rule_num = None
    last_title = None
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        
        # Skip empty lines at the very beginning
        if not stripped and not pass1_lines:
            i += 1
            continue

        # Check against header patterns
        is_header_footer = False
        for pattern in header_patterns:
            if re.match(pattern, stripped, re.IGNORECASE):
                is_header_footer = True
                break
        
        if is_header_footer:
            i += 1
            continue

        # Check for RULE headers (case insensitive)
        rule_match = re.match(r'^###\s*Rule\s*(\d+)', stripped, re.IGNORECASE)
        if rule_match:
            rule_num = rule_match.group(1)
            normalized_rule = f"### RULE {rule_num}"
            
            next_line = ""
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    next_line = lines[j].strip()
                    break
            
            if rule_num == last_rule_num:
                i += 1
                if next_line.upper() == (last_title or "").upper():
                    # Skip the next title too, but ONLY if it's within the next few lines
                    next_found = False
                    for j in range(i, min(i + 20, len(lines))):
                        if lines[j].strip() == next_line:
                            i = j + 1
                            next_found = True
                            break
                    if not next_found: i += 1
                continue
            else:
                last_rule_num = rule_num
                last_title = next_line
                pass1_lines.append(normalized_rule + "\n")
                i += 1
                continue
        
        # Bracket removal: [S]ection -> Section
        line = re.sub(r'\[([a-zA-Z])\]', r'\1', line)
        
        # Bleed-in fixes
        line = re.sub(r'Section (\d+)\.\s*[a-z]+;\s*', r'Section \1. ', line)
        
        pass1_lines.append(line + "\n")
        i += 1

    # Pass 2: Join split paragraphs
    pass2_lines = []
    i = 0
    while i < len(pass1_lines):
        line = pass1_lines[i].rstrip()
        
        if not line:
            pass2_lines.append("\n")
            i += 1
            continue
            
        # Join condition: 
        # 1. Current line doesn't end in terminal punctuation
        # 2. Not a Rule header
        no_terminal = not re.search(r'[.!?:"”)]\s*(?:\([^)]+\))?\s*$', line)
        is_header = line.startswith('###')
        
        if no_terminal and not is_header:
            # Look ahead for next non-empty line (within limit)
            next_idx = i + 1
            found_continuation = False
            # Limit lookahead to avoid joining across deleted sections or huge gaps
            while next_idx < min(i + 10, len(pass1_lines)):
                next_line = pass1_lines[next_idx].strip()
                if not next_line:
                    next_idx += 1
                    continue
                
                # If next line looks like a continuation
                is_next_break = (next_line.startswith('###') or 
                                 next_line.startswith('Section') or 
                                 next_line.startswith('Rule') or
                                 re.match(r'^\([a-z]\)', next_line))
                
                if not is_next_break:
                    line = line + " " + next_line
                    i = next_idx 
                    found_continuation = True
                    break
                else:
                    break
            
            if not found_continuation:
                pass2_lines.append(line + "\n")
                i += 1
            else:
                continue
        else:
            pass2_lines.append(line + "\n")
            i += 1

    # Final pass: remove triple empty lines
    final_lines = []
    empty_count = 0
    for line in pass2_lines:
        if not line.strip():
            empty_count += 1
        else:
            if empty_count > 0:
                final_lines.append("\n")
                empty_count = 0
            final_lines.append(line)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
    
    print(f"Cleaned file saved to {output_path}")
    print(f"Original lines: {len(lines)}, Cleaned lines: {len(final_lines)}")

if __name__ == "__main__":
    input_file = r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC\Combined_Rules_of_Court.md'
    output_file = r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC\Combined_Rules_of_Court_Cleaned.md'
    clean_markdown(input_file, output_file)
