
from pathlib import Path
import os

BASE_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")

def audit_files():
    total_files = 0
    small_files = 0
    empty_files = 0
    
    print(f"Scanning {BASE_DIR}...")
    
    for year_dir in BASE_DIR.iterdir():
        if not year_dir.is_dir(): continue
        
        for html_file in year_dir.glob("*.html"):
            total_files += 1
            size = html_file.stat().st_size
            
            if size == 0:
                empty_files += 1
                # print(f"EMPTY: {html_file}")
            elif size < 2000:
                small_files += 1
                print(f"SMALL ({size}b): {html_file}")
                
    print(f"Total Files: {total_files}")
    print(f"Empty Files: {empty_files}")
    print(f"Small Files (<2KB): {small_files}")

if __name__ == "__main__":
    audit_files()
