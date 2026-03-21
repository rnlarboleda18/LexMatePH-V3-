import os
import re
from pathlib import Path

TRUNCATED_LIST = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\truncated_files_1975_2025.txt"
MD_ROOT = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")

def get_skipped_files():
    with open(TRUNCATED_LIST, 'r') as f:
        all_targets = [line.strip() for line in f if line.strip()]
    
    skipped = []
    for md_rel_path in all_targets:
        md_path = MD_ROOT / md_rel_path
        # If the file hasn't been updated today (Dec 19), it was likely skipped or the update failed
        # Actually, let's just check the size. If it's still very small, it's truncated.
        if md_path.exists():
            if md_path.stat().st_size < 10000: # Threshold for truncated
                skipped.append(md_rel_path)
        else:
             skipped.append(md_rel_path)
    return skipped

user_specific_2015 = [
    r"2015\G.R. No. 189649-2015_January_01_2015.md",
    r"2015\G.R. No. 190112-2015_January_01_2015.md",
    r"2015\G.R. No. 191667-2015_January_01_2015.md",
    r"2015\G.R. No. 192698-2015_January_01_2015.md",
    r"2015\G.R. No. 193101-2015_January_01_2015.md",
    r"2015\G.R. No. 193169-2015_January_01_2015.md",
    r"2015\G.R. No. 194061-2015_January_01_2015.md",
    r"2015\G.R. No. 194339-2015_January_01_2015.md",
    r"2015\G.R. No. 194702-2015_January_01_2015.md",
    r"2015\G.R. No. 195203-2015_January_01_2015.md",
    r"2015\G.R. No. 196357-2015_January_01_2015.md",
    r"2015\G.R. No. 196592-2015_January_01_2015.md",
    r"2015\G.R. No. 197562-2015_January_01_2015.md",
    r"2015\G.R. No. 197597-2015_January_01_2015.md",
    r"2015\G.R. No. 197712-2015_January_01_2015.md",
    r"2015\G.R. No. 198012-2015_January_01_2015.md",
    r"2015\G.R. No. 198356-2015_January_01_2015.md",
    r"2015\G.R. No. 198465-2015_January_01_2015.md",
    r"2015\G.R. No. 198543-2015_January_01_2015.md",
    r"2015\G.R. No. 199166-2015_January_01_2015.md",
    r"2015\G.R. No. 200465-2015_January_01_2015.md",
    r"2015\G.R. No. 201146-2015_January_01_2015.md",
    r"2015\G.R. No. 202331-2015_January_01_2015.md",
    r"2015\G.R. No. 202708-2015_January_01_2015.md",
    r"2015\G.R. No. 202950-2015_January_01_2015.md",
    r"2015\G.R. No. 203530-2015_January_01_2015.md",
    r"2015\G.R. No. 203804-2015_January_01_2015.md",
    r"2015\G.R. No. 203993-2015_January_01_2015.md",
    r"2015\G.R. No. 204171-2015_January_01_2015.md",
    r"2015\G.R. No. 204646-2015_January_01_2015.md",
    r"2015\G.R. No. 205188-2015_January_01_2015.md",
    r"2015\G.R. No. 206020-2015_January_01_2015.md",
    r"2015\G.R. No. 206540-2015_January_01_2015.md",
    r"2015\G.R. No. 207328-2015_January_01_2015.md",
    r"2015\G.R. No. 208062-2015_January_01_2015.md",
    r"2015\G.R. No. 208163-2015_January_01_2015.md",
    r"2015\G.R. No. 209537-2015_January_01_2015.md",
    r"2015\G.R. No. 209741-2015_January_01_2015.md",
    r"2015\G.R. No. 211833-2015_January_01_2015.md",
    r"2015\G.R. No. 211933-2015_January_01_2015.md",
    r"2015\G.R. No. 212092-2015_January_01_2015.md",
    r"2015\G.R. No. 212381-2015_January_01_2015.md"
]

def extract_case_info(md_rel_path):
    # E.g. 2015\G.R. No. 189649-2015_January_01_2015.md
    # Or 2015/G.R. No. 193890_March_11_2015.md
    basename = os.path.basename(md_rel_path)
    year_match = re.search(r'(\d{4})', md_rel_path)
    year = year_match.group(1) if year_match else "Unknown"
    
    # Extract G.R. No.
    gr_match = re.search(r'G\.R\. No\. ([A-Z\d\-\.]+)', basename)
    if gr_match:
        gr_no = gr_match.group(1).replace('-', ' ') # Lawphil uses spaces usually but user provided dashes
        # Sometimes there's a year suffix in the case number itself in the user list like 189649-2015
        gr_no = re.sub(r'-\d{4}$', '', gr_no)
        return {"year": year, "gr_no": gr_no, "origin": md_rel_path}
    return None

if __name__ == "__main__":
    skipped = get_skipped_files()
    all_md_targets = list(set(skipped + user_specific_2015))
    
    targets = []
    for t in all_md_targets:
        info = extract_case_info(t)
        if info:
            targets.append(info)
    
    print(f"Total targets identified: {len(targets)}")
    
    # Save targets for the scraper
    import json
    with open("rescrape_targets.json", "w") as f:
        json.dump(targets, f, indent=2)
    print("Saved rescrape_targets.json")
