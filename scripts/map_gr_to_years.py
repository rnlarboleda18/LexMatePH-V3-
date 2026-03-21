import os
import re
import json
from pathlib import Path

TRUNCATED_LIST_PATH = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\truncated_files_1975_2025.txt"
USER_2015_MD = [
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

def extract_info(path):
    year_match = re.search(r'(\d{4})', path)
    year = year_match.group(1) if year_match else None
    
    gr_match = re.search(r'G\.R\. No\. ([A-Z\d\.\- ]+)', os.path.basename(path))
    if gr_match:
        gr = gr_match.group(1).split('_')[0].split('-2015')[0].strip()
        return {"gr": gr, "year": year}
    return None

if __name__ == "__main__":
    with open(TRUNCATED_LIST_PATH, 'r') as f:
        truncated = [line.strip() for line in f if line.strip()]
    
    mapping = {}
    for p in truncated + USER_2015_MD:
        info = extract_info(p)
        if info:
            gr = info['gr']
            year = info['year']
            if gr not in mapping:
                mapping[gr] = set()
            if year:
                mapping[gr].add(year)
    
    # Convert sets to lists for JSON
    serializable = {k: list(v) for k, v in mapping.items()}
    
    with open("gr_year_mapping.json", "w") as f:
        json.dump(serializable, f, indent=2)
    
    years = set()
    for y_list in serializable.values():
        for y in y_list:
            years.add(y)
            
    print(f"Total Unique G.R. Nos: {len(serializable)}")
    print(f"Years involved: {sorted(list(years))}")
