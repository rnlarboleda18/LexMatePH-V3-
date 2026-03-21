import os
import shutil
from pathlib import Path

BASE_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")
BAD_DIR = BASE_DIR / "2105"
TARGET_DIR = BASE_DIR / "2015"

def fix_2105_typo():
    if not BAD_DIR.exists():
        print(f"Directory {BAD_DIR} does not exist. Nothing to do.")
        return

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    files = list(BAD_DIR.glob("*.md"))
    print(f"Found {len(files)} files in {BAD_DIR}")
    
    for file_path in files:
        # 1. Read Content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 2. Fix Content
            if "2105" in content:
                new_content = content.replace("2105", "2015")
                # Safety check: Avoid "12105" or similar if possible, but 2105 is distinct enough here
            else:
                new_content = content
                print(f"Warning: '2105' not found in content of {file_path.name}")
                
            # 3. Determine New Filename
            new_name = file_path.name.replace("2105", "2015")
            target_path = TARGET_DIR / new_name
            
            # 4. Write to New Location
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            print(f"Moved & Fixed: {file_path.name} -> {target_path}")
            
            # 5. Delete Old File
            os.remove(file_path)
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    # 6. Remove Bad Directory if empty
    if not any(BAD_DIR.iterdir()):
        try:
            BAD_DIR.rmdir()
            print(f"Removed empty directory: {BAD_DIR}")
        except Exception as e:
            print(f"Could not remove directory {BAD_DIR}: {e}")
    else:
        print(f"Directory {BAD_DIR} is not empty, skipping removal.")

if __name__ == "__main__":
    fix_2105_typo()
