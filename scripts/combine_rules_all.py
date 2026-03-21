import os
import time

OUT_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC"
TARGET = os.path.join(OUT_DIR, "Combined_Rules_of_Court.md")

SEQUENCE = [
    "1. ROC Civil Procedure as amended 2019.md",
    "2. ROC Special Proceeding.md",
    "3. ROC Criminal Procedure.md",
    "4. ROC Evidence as amended 2019.md"
]

def combine():
    print(f"Combination script started. Target: {TARGET}")
    while True:
        all_exist = True
        missing = []
        for f in SEQUENCE:
             path = os.path.join(OUT_DIR, f)
             if not os.path.exists(path):
                  all_exist = False
                  missing.append(f)
        if all_exist:
             break
        print(f"Waiting for files: {missing}...")
        time.sleep(30)
        
    print(f"\n🔗 All files present! Combining into {TARGET}...")
    with open(TARGET, 'w', encoding='utf-8') as outfile:
         for f in SEQUENCE:
              path = os.path.join(OUT_DIR, f)
              with open(path, 'r', encoding='utf-8') as infile:
                   content = infile.read()
                   outfile.write(f"\n\n# {f.split('. ', 1)[1].rsplit('.', 1)[0]}\n\n")
                   outfile.write(content)
                   outfile.write("\n\n---\n")
    print("🎉 Combined file successfully created!")

if __name__ == "__main__":
    combine()
