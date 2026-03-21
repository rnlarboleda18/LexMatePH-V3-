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
    
    for filename in files:
        path = os.path.join(dir_path, filename)
        if not os.path.exists(path):
            print(f"File not found: {filename}")
            continue
            
        print(f"\n--- rules in {filename} ---")
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Just print the FIRST rule found in the file to see the starting point
            found_rules = []
            for line in lines:
                match = rule_pattern.match(line)
                if match:
                    found_rules.append(match.group(1).upper())
                    
            if found_rules:
                print(f"First Rule: {found_rules[0]}")
                print(f"Last Rule: {found_rules[-1]}")
                print(f"Total Rules: {len(found_rules)}")
            else:
                print("No rules found.")

if __name__ == "__main__":
    inspect_rules()
