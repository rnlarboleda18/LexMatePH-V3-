import os
import re

def inspect_rules_detail():
    dir_path = r"CodexPhil\Codals\md\ROC"
    
    # 1. List ALL rules in Civil Procedure to verify 144
    civ_path = os.path.join(dir_path, "1. ROC Civil Procedure as amended 2019.md")
    rule_pattern = re.compile(r'^###\s+(RULE\s+\d+)', re.IGNORECASE)
    
    output = []
    output.append("=== Civil Procedure Rules ===")
    if os.path.exists(civ_path):
        with open(civ_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = rule_pattern.match(line)
                if match:
                    output.append(match.group(1).upper())
                    
    # 2. Inspect Criminal Procedure for ANY Rule format
    crim_path = os.path.join(dir_path, "3. ROC Criminal Procedure.md")
    output.append("\n=== Criminal Procedure Sample Lines ===")
    if os.path.exists(crim_path):
        with open(crim_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Print lines containing "Rule" to see format
            for i, line in enumerate(lines[:500]): # Check first 500 lines
                if 'Rule' in line or 'RULE' in line:
                    output.append(f"Line {i+1}: {line.strip()}")
                    
    with open(r"api\roc_detail_inspection.txt", 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

if __name__ == "__main__":
    inspect_rules_detail()
