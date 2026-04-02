import re
import os

def clean_and_combine():
    base_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\clean\ROC"
    source_files = [
        "1. ROC Civil Procedure as amended 2019.md",
        "2. ROC Special Proceeding.md",
        "3. ROC Criminal Procedure.md",
        "4. ROC Evidence as amended 2019.md"
    ]
    
    header_patterns = [
        r'^ROC Civil Procedure as amended 2019$',
        r'^ROC Special Proceeding$',
        r'^ROC Criminal Procedure$',
        r'^ROC Evidence as amended 2019$',
        r'^\*\*RULES OF COURT\*\*',
        r'^RULES OF COURT$',
        r'^.*2019 AMENDMENTS TO THE.*RULES.*PROCEDURE.*',
        r'^.*2019 AMENDMENTS TO THE .*RULES ON EVIDENCE.*',
        r'^PROCEDURE IN REGIONAL TRIAL COURTS$',
        r'^\s*\d+\s*$', # Page numbers
        r'^Page \d+$',
        r'^---+$', # Horizontal rules
    ]
    
    all_content_lines = []
    
    for filename in source_files:
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
            
        print(f"Processing {filename}...")
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Add a section separator header
        section_name = filename.split('.')[1].strip().upper()
        # all_content_lines.append(f"\n\n# {section_name}\n\n")
        
        # Pass 1: Local cleaning for this file
        file_lines = []
        last_rule_num = None
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()
            
            if not stripped:
                file_lines.append("\n")
                i += 1
                continue
                
            if "Scope of examination" in stripped:
                print(f"DEBUG: Found Scope of examination in {filename} at line {i}")
            
            # Filter headers/footers
            skip = False
            for p in header_patterns:
                if re.match(p, stripped, re.IGNORECASE):
                    skip = True
                    break
            if skip:
                if "Scope of examination" in stripped: print("DEBUG: Skipped by header_patterns")
                i += 1
                continue
                
            # Rule duplicate check
            rule_match = re.match(r'^###\s*Rule\s*(\d+)', stripped, re.IGNORECASE)
            if rule_match:
                r_num = rule_match.group(1)
                if r_num == last_rule_num:
                    if "Scope of examination" in stripped: print("DEBUG: Skipped by duplicate rule check")
                    i += 1
                    continue
                last_rule_num = r_num
                file_lines.append(f"### RULE {r_num}\n")
                i += 1
                continue

            # Bracket removal
            line = re.sub(r'\[([a-zA-Z])\]', r'\1', line)
            
            # Bleed-in fixes
            line = re.sub(r'Section (\d+)\.\s*[a-z]+;\s*', r'Section \1. ', line)
            
            if "Scope of examination" in stripped: print("DEBUG: Appending to file_lines")
            file_lines.append(line + "\n")
            i += 1
        
        all_content_lines.extend(file_lines)

    print(f"Total lines collected in all_content_lines: {len(all_content_lines)}")

    # Pass 2: Safe Joining
    pass2_lines = []
    i = 0
    while i < len(all_content_lines):
        line = all_content_lines[i].rstrip()
        
        if not line:
            pass2_lines.append("\n")
            i += 1
            continue
            
        if "Scope of examination" in line:
            print(f"DEBUG Pass 2: Current line contains Scope of examination. line starts with: '{line[:20]}'")

        # Join condition: 
        # 1. Current line doesn't end in terminal punctuation
        # 2. Not a Rule header
        no_terminal = not re.search(r'[.!?:"”)]\s*(?:\([^)]+\))?\s*$', line)
        is_dash_continuation = line.endswith('-')
        is_header = line.startswith('###')
        
        if (no_terminal or is_dash_continuation) and not is_header:
            # Look ahead for next non-empty line (within max 5 lines)
            next_idx = i + 1
            found = False
            while next_idx < min(i + 6, len(all_content_lines)):
                next_line = all_content_lines[next_idx].strip()
                if not next_line:
                    next_idx += 1
                    continue
                
                if "Scope of examination" in next_line:
                    print(f"DEBUG Pass 2: Next line contains Scope of examination. next_line starts with: '{next_line[:20]}'")

                # Continuation if not a break AND starts with lowercase
                is_break = (next_line.startswith('###') or 
                            next_line.startswith('Section') or 
                            next_line.startswith('Rule') or
                            re.match(r'^\([a-z]\)', next_line))
                
                # Strong signal: starts with lowercase
                is_continuation = re.match(r'^[a-z]', next_line)
                
                if not is_break and is_continuation:
                    if "Scope of examination" in next_line or "Scope of examination" in line:
                        print(f"DEBUG Pass 2: JOINING lines. Line ends with '{line[-10:]}', next_line starts with '{next_line[:20]}'")
                    # Join them
                    if is_dash_continuation:
                        line = line.rstrip('-') + next_line
                    else:
                        line = line + " " + next_line
                    i = next_idx
                    found = True
                    break
                else:
                    break
            
            if found:
                # We updated 'line', continue to see if more joins are possible
                continue
            else:
                pass2_lines.append(line + "\n")
                i += 1
        else:
            pass2_lines.append(line + "\n")
            i += 1
            
    # Remove triple blank lines
    result = []
    e_count = 0
    for line in pass2_lines:
        if not line.strip():
            e_count += 1
        else:
            if e_count > 0:
                result.append("\n")
                e_count = 0
            result.append(line)
            
    output_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\clean\ROC\Combined_Rules_of_Court.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(result)
    print(f"Successfully combined and cleaned {len(result)} lines into {output_path}")

if __name__ == "__main__":
    clean_and_combine()
