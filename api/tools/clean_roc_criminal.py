import os
import re

def clean_criminal_proc():
    path = r"LexCode\Codals\md\ROC\3. ROC Criminal Procedure.md"
    out_path = r"LexCode\Codals\md\ROC\3. ROC Criminal Procedure_cleaned.md"
    
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Standardize RULE headers that might be jammed at the end of a line
    # Replace **RULE 116 with \n\n### RULE 116\n
    content = re.sub(r'\*\*RULE\s+(\d+)', r'\n\n### RULE \1\n', content)

    lines = content.split('\n')
    cleaned = []
    
    sec_pat = re.compile(r'^([A-Z\s,]+)\*\*\*\*SECTION\s+(\d+)\..*', re.IGNORECASE) # Match PROSECUTION OF OFFENSES****SECTION 1.
    sec_simple_pat = re.compile(r'^\*\*Sec\.\s+(\d+)\.', re.IGNORECASE) # Match **Sec. 14.
    section_capital_pat = re.compile(r'^\*\*SECTION\s+(\d+)\..*', re.IGNORECASE) # Match **SECTION 1.

    for line in lines:
        line_stripped = line.strip()
        
        # 2. Match Jammed Title + Section
        sec_match = sec_pat.match(line_stripped)
        if sec_match:
            title = sec_match.group(1).strip()
            sec_num = sec_match.group(2).strip()
            cleaned.append(f"## {title}\n")
            rest = line_stripped.split('****')[1]
            rest_cleaned = rest.replace('SECTION', 'Section')
            cleaned.append(f"{rest_cleaned}\n")
            continue

        # 3. Match **Sec. X.
        if sec_simple_pat.match(line_stripped):
            cleaned.append(line_stripped.replace('**Sec.', 'Section').replace('**', '') + "\n")
            continue
            
        # 4. Match **SECTION X.
        if section_capital_pat.match(line_stripped):
             cleaned.append(line_stripped.replace('**SECTION', 'Section').replace('**', '') + "\n")
             continue

        # Default
        cleaned.append(line + "\n")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned)
    print(f"Cleaned file saved to {out_path}")

if __name__ == "__main__":
    clean_criminal_proc()
