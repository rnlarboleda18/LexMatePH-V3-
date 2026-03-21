import os
import re

ROC_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC"

def main():
    files = [
        "1. ROC Civil Procedure as amended 2019.md",
        "2. ROC Special Proceeding.md",
        "3. ROC Criminal Procedure.md",
        "4. ROC Evidence as amended 2019.md"
    ]

    for f in files:
        path = os.path.join(ROC_DIR, f)
        if not os.path.exists(path):
            print(f"Skipping {f} (Missing)")
            continue
            
        print(f"\n--- {f} ---")
        with open(path, 'r', encoding='utf-8') as f_in:
             lines = f_in.readlines()
             
        # Find all `##` and `###` headers, and the approximate Rule/Section following them
        current_header = None
        for i, l in enumerate(lines):
             l_strip = l.strip()
             if l_strip.startswith("## ") or l_strip.startswith("### "):
                  # Exclude RULE labels themselves from sub-heading categorization
                  if "RULE " in l_strip.upper():
                       print(f"  Pos {i+1}: {l_strip} (Rule Marker)")
                  else:
                       print(f"  Pos {i+1}: SUBHEADER -> {l_strip}")
                       
             elif "RULE " in l_strip.upper():
                  # Sometimes rule sits in its own standalone paragraph or text line
                  if l_strip.startswith("#"):
                       print(f"  Pos {i+1}: {l_strip}")
                  else:
                       print(f"  Pos {i+1}: Rule standalone: {l_strip}")

if __name__ == "__main__":
    main()
