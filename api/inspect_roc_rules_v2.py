import os
import re

def inspect_rules():
    dir_path = r"CodexPhil\Codals\md\ROC"
    files = [
        "1. ROC Civil Procedure as amended 2019.md",
        "2. ROC Special Proceeding.md",
        "3. ROC Criminal Procedure.md",
        "4. ROC Evidence as amended 2019.md"
    ]
    
    rule_pattern = re.compile(r'^###\s+(RULE\s+\d+)', re.IGNORECASE)
    
    output_lines = []
    
    for filename in files:
        path = os.path.join(dir_path, filename)
        if not os.path.exists(path):
            output_lines.append(f"File not found: {filename}")
            continue
            
        output_lines.append(f"\n--- rules in {filename} ---")
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            found_rules = []
            for line in lines:
                match = rule_pattern.match(line)
                if match:
                    found_rules.append(match.group(1).upper())
                    
            if found_rules:
                output_lines.append(f"First Rule: {found_rules[0]}")
                output_lines.append(f"Last Rule: {found_rules[-1]}")
                output_lines.append(f"Total Rules: {len(found_rules)}")
            else:
                output_lines.append("No rules found.")

    output_path = r"api\roc_inspection_results.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print(f"Results written to {output_path}")

if __name__ == "__main__":
    inspect_rules()
