
import os

OLD_NAME = "generate_sc_digests_gemini.py"
NEW_NAME = "generate_sc_digests_gemini.py"
ROOT_DIR = "."

def fix_references():
    print(f"Scanning for references to {OLD_NAME}...")
    count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".gemini" in root or "__pycache__" in root or ".git" in root:
            continue
            
        for file in files:
            if file.endswith(".ps1") or file.endswith(".py") or file.endswith(".err"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if OLD_NAME in content:
                        # Avoid double replacement if already fixed (unlikely but safe)
                        if NEW_NAME in content and OLD_NAME not in content.replace(NEW_NAME, ""):
                             continue

                        print(f"Fixing {path}...")
                        new_content = content.replace(OLD_NAME, NEW_NAME)
                        
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        count += 1
                except Exception as e:
                    print(f"Skipping {path}: {e}")
                    
    print(f"Fixed references in {count} files.")

if __name__ == "__main__":
    fix_references()
