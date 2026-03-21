import os
import re
import shutil
from pathlib import Path
from datetime import datetime
import concurrent.futures
import multiprocessing

ROOT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")

def parse_filename_date(fname):
    # Format: G.R. No. 12345_Month_DD_YYYY.md
    match = re.search(r'_([A-Z][a-z]+)_(\d{2})_(\d{4})\.md$', fname)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)} {match.group(2)}, {match.group(3)}", "%B %d, %Y")
        except:
            return None
    return None

def extract_header_date(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = [f.readline().strip() for _ in range(20)]
            
        # Robust regex from verify_dates_with_gemini.py
        date_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})', re.IGNORECASE)
        
        for line in lines:
            if not line: continue
            # Check for header markers (optional, but good for safety)
            # if line.startswith("###") or line.startswith("**"): 
            
            match = date_pattern.search(line)
            if match:
                month, day, year = match.groups()
                try:
                    return datetime.strptime(f"{month} {day}, {year}", "%B %d, %Y")
                except:
                    continue
        return None
    except Exception:
        return None

def process_file(file_path):
    try:
        fname = file_path.name
        f_date = parse_filename_date(fname)
        h_date = extract_header_date(file_path)
        
        if not h_date:
            return {"status": "skipped", "reason": "no_header_date"}
            
        if not f_date:
             # Filename format is weird, but we have a header date. Let's rename it!
             pass 
        elif f_date == h_date:
            return {"status": "ok"} # No change needed
            
        # MISMATCH DETECTED - REORGANIZE
        
        # New Filename Construction
        # We need to preserve the Case Number part.
        # Strict assumption: Case Number is everything BEFORE the date part in filename
        # OR just take the whole string before the date regex
        
        base_name_match = re.search(r'^(.*)_([A-Z][a-z]+)_(\d{2})_(\d{4})\.md$', fname)
        if base_name_match:
            case_prefix = base_name_match.group(1)
        else:
            # Fallback if filename didn't match standard format (e.g. maybe it lacked date entirely)
            case_prefix = fname.replace(".md", "")
            
        new_year = h_date.year
        new_month = h_date.strftime("%B")
        new_day = h_date.strftime("%d")
        
        new_fname = f"{case_prefix}_{new_month}_{new_day}_{new_year}.md"
        new_dir = ROOT_DIR / str(new_year)
        new_path = new_dir / new_fname
        
        # Create dir if not exists (might race condition in threads? check exists first)
        # Better: return the intent, let main thread move? No, 50 workers need to enable IO.
        # makedirs is largely thread safe on OS level usually, or we catch error
        new_dir.mkdir(parents=True, exist_ok=True)
        
        # Check collision
        if new_path.exists() and new_path != file_path:
             # If target exists, maybe append counter?
             return {"status": "error", "reason": "target_exists", "target": str(new_path)}
        
        # MOVE
        shutil.move(file_path, new_path)
        
        return {
            "status": "moved", 
            "original": str(file_path), 
            "new": str(new_path),
            "old_date": f_date.strftime("%Y-%m-%d") if f_date else "None",
            "new_date": h_date.strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def run_reorg(workers=50):
    print("Listing files...")
    all_files = list(ROOT_DIR.rglob("*.md"))
    print(f"Found {len(all_files)} files. Starting Reorganization with {workers} workers...")
    
    stats = {"ok": 0, "moved": 0, "skipped": 0, "error": 0}
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_file, p): p for p in all_files}
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            res = future.result()
            stats[res['status']] += 1
            
            if res['status'] == 'moved':
                print(f"[MOVED] {Path(res['original']).name} -> {Path(res['new']).name} ({res['new_date']})")
            elif res['status'] == 'error':
                print(f"[ERROR] {futures[future].name}: {res['reason']}")
                
            if i % 1000 == 0:
                print(f"Progress: {i}/{len(all_files)}... Stats: {stats}")

    print("="*50)
    print("Reorganization Complete.")
    print(stats)
    
    # Cleanup empty directories
    print("Cleaning up empty directories...")
    for year_dir in ROOT_DIR.iterdir():
        if year_dir.is_dir() and not any(year_dir.iterdir()):
             try:
                 year_dir.rmdir()
                 print(f"Removed empty dir: {year_dir}")
             except:
                 pass

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_reorg(50)
