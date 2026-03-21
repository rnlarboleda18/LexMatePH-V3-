import os
import re
import shutil
from pathlib import Path
import concurrent.futures
from tqdm import tqdm

ROOT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")

def normalize_filename(file_path):
    fname = file_path.name
    
    # Pattern: CaseNo - OpinionType_Month_DD_YYYY.md
    # Note: Using robust date regex from previous steps
    pattern = re.compile(r'^(.*)\s+-\s+(.*)_(January|February|March|April|May|June|July|August|September|October|November|December)_(\d{2})_(\d{4})\.md$', re.IGNORECASE)
    
    match = pattern.match(fname)
    if not match:
        return None
    
    case_no = match.group(1).strip()
    opinion_type_raw = match.group(2).strip()
    month = match.group(3)
    day = match.group(4)
    year = match.group(5)
    
    # Normalize Opinion Type: "Concurring & Dissenting Opinion" -> "Concurring_&_Dissenting_Opinion"
    # User requested: "Concurring Opinion" -> "Concurring_Opinion"
    opinion_type = opinion_type_raw.replace(" ", "_").replace("&", "and") # Sanitize & just in case, though user showed spaces replaced
    
    # Wait, user example: "Concurring_Opinion"
    # Actually, let's keep it close to user request.
    # User Request: "A.C. No. 7121 (Formerly CBD Case No. 04-1244) March_08_2022_Concurring_Opinion"
    
    new_fname = f"{case_no}_{month}_{day}_{year}_{opinion_type}.md"
    new_path = file_path.parent / new_fname
    
    if new_fname == fname:
        return None
        
    return {
        "original_path": file_path,
        "new_path": new_path,
        "case_no": case_no,
        "date_str": f"{month} {day}, {year}",
        "opinion_type": opinion_type
    }

def process_file(file_path):
    try:
        rename_op = normalize_filename(file_path)
        if not rename_op:
            return {"status": "skipped"}
        
        original = rename_op["original_path"]
        target = rename_op["new_path"]
        
        if target.exists():
             return {"status": "error", "reason": "Target exists", "target": str(target)}
             
        shutil.move(original, target)
        return {"status": "renamed", "from": original.name, "to": target.name}
        
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def run_normalization():
    print("Scanning for opinion files...")
    # Filter for files likely to contain "Opinion" to save time, or just scan all md
    # Scanning all is safer to catch weird variations
    all_files = list(ROOT_DIR.rglob("*Opinion*.md"))
    
    print(f"Found {len(all_files)} potential files.")
    
    stats = {"renamed": 0, "skipped": 0, "error": 0}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(process_file, p): p for p in all_files}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(all_files)):
            res = future.result()
            stats[res['status']] += 1
            if res['status'] == 'error':
                 print(f"[ERR] {res.get('reason')} - {res.get('target', '')}")

    print("\nRenaming Complete.")
    print(stats)

if __name__ == "__main__":
    run_normalization()
