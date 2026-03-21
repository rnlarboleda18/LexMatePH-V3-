import os
import re
import json

ROC_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC"

def main():
    files = [
        "1. ROC Civil Procedure as amended 2019.md",
        "2. ROC Special Proceeding.md",
        "3. ROC Criminal Procedure.md",
        "4. ROC Evidence as amended 2019.md"
    ]

    all_data = {}

    for f in files:
        path = os.path.join(ROC_DIR, f)
        if not os.path.exists(path):
            continue
            
        print(f"Processing {f}...")
        with open(path, 'r', encoding='utf-8') as f_in:
             lines = f_in.readlines()
             
        file_headers = []
        current_rule = None
        current_section = None
        
        for i, l in enumerate(lines):
             l_strip = l.strip()
             if l_strip.startswith("## ") or l_strip.startswith("### "):
                  if "RULE " in l_strip.upper():
                       current_rule = l_strip
                       current_section = None # Reset on new rule
                  else:
                       file_headers.append({
                           "line": i + 1,
                           "type": "header",
                           "text": l_strip,
                           "after_rule": current_rule,
                           "after_section": current_section
                       })
             elif "RULE " in l_strip.upper():
                  current_rule = l_strip
                  current_section = None
             elif l_strip.startswith("Section ") and "." in l_strip:
                  # Extract section number e.g. "Section 1." -> "1"
                  match = re.search(r'Section\s+(\d+)\.', l_strip)
                  if match:
                       current_section = match.group(1)

        all_data[f] = file_headers

    output_path = os.path.join(os.path.dirname(__file__), "roc_headers_extracted.json")
    with open(output_path, 'w', encoding='utf-8') as f_out:
         json.dump(all_data, f_out, indent=2)

    print(f"\n🎉 Saved all headers to {output_path}")

if __name__ == "__main__":
    main()
