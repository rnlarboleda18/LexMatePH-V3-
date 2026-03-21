
import json
import difflib
import random
from pathlib import Path
from bs4 import BeautifulSoup

# Configuration
SC_SCRAPER_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper")
REPORT_FILE = SC_SCRAPER_DIR / "collision_report.json"
SAMPLE_SIZE = 50  # Check 50 random groups (or all if low count)

def clean_text(text):
    """Normalize text for comparison (ignore whitespace differences)"""
    return ' '.join(text.split())

def check_group(key, files):
    """
    Compares the first two files in a group.
    Returns (is_identical, diff_text)
    """
    if len(files) < 2:
        return True, "Single file (no duplicate)"
        
    path1 = files[0]['path']
    path2 = files[1]['path']
    
    try:
        with open(path1, "r", encoding="utf-8", errors="ignore") as f1, \
             open(path2, "r", encoding="utf-8", errors="ignore") as f2:
            content1 = f1.read()
            content2 = f2.read()
            
        # Parse and get text to ignore HTML structure differences if any (or should we check HTML too?)
        # User wants to know if they are "really duplicates". 
        # Usually checking text content is sufficient for legal docs.
        # But let's check text first.
        
        soup1 = BeautifulSoup(content1, "lxml")
        soup2 = BeautifulSoup(content2, "lxml")
        
        text1 = soup1.get_text("\n", strip=True) # Use newline separator to keep structure
        text2 = soup2.get_text("\n", strip=True)
        
        if text1 == text2:
            return True, None
            
        # If texts differ, normalize whitespace and try again
        norm1 = clean_text(text1)
        norm2 = clean_text(text2)
        
        if norm1 == norm2:
            return True, "Whitespace difference only"
            
        # If still different, generate diff
        diff = difflib.unified_diff(
            text1.splitlines(), 
            text2.splitlines(), 
            fromfile=Path(path1).name, 
            tofile=Path(path2).name,
            lineterm=''
        )
        return False, '\n'.join(list(diff)[:10]) # First 10 lines of diff
        
    except Exception as e:
        return False, f"Error reading files: {e}"

def main():
    if not REPORT_FILE.exists():
        print("Report file not found.")
        return

    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # We want to check "true_duplicates" if it exists in the json, 
    # BUT audit_collisions.py might not have saved it to save space?
    # Let's check the distinct_collisions section in the file I just viewed...
    # Wait, the previous file view showed "distinct_collisions" but I didn't see "true_duplicates" key in the snippet.
    # The audit script had: # "true_duplicates": true_duplicates # Optional: exclude to save space if needed
    # If I excluded it, I can't verify it!
    
    # Re-reading audit_collisions.py code or report content...
    # The view_file output of collision_report.json showed:
    # "distinct_collisions": { ... }
    # It did NOT show "true_duplicates" key at the root level in the first 11 lines.
    # But I see in the previous turn's `audit_collisions.py` code:
    #     report = { ..., "distinct_collisions": distinct_collisions, ... }
    #     # "true_duplicates": true_duplicates # Optional: exclude to save space if needed
    
    # Ah, I see I commented it out in the code I wrote?
    # Let me check if I actually wrote it to the file.
    
    true_dups = data.get("true_duplicates", {})
    
    if not true_dups:
        # If I didn't save them, I need to re-scan OR just use the summary count?
        # User wants me to investigate THEM.
        # If I didn't save the paths, I have to re-run the audit to find them labels.
        # OR I can re-run audit specifically for duplicates.
        
        print("Detailed 'true_duplicates' list not found in report (likely optimized out).")
        print("Re-running targeted audit to find them...")
        
        # We can reuse the audit logic but this time we explicitly look for the duplicates.
        from audit_collisions import process_file_audit, DOWNLOADS_DIR
        import concurrent.futures
        from collections import defaultdict
        
        # Simplified Re-Audit
        all_files = list(DOWNLOADS_DIR.rglob("*.html"))
        results_by_key = defaultdict(list)
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=20) as executor:
            future_to_file = {executor.submit(process_file_audit, f): f for f in all_files}
            for future in concurrent.futures.as_completed(future_to_file):
                res = future.result()
                if res:
                    results_by_key[res["key"]].append(res)
                    
        # Re-construct true_dups
        true_dups = {}
        for key, file_list in results_by_key.items():
            if len(file_list) > 1:
                hashes = set(f["hash"] for f in file_list)
                if len(hashes) == 1:
                    true_dups[key] = file_list
        
    print(f"Found {len(true_dups)} True Duplicate groups.")
    
    # Sample and Verify
    keys = list(true_dups.keys())
    sample_keys = random.sample(keys, min(SAMPLE_SIZE, len(keys)))
    
    discrepancies = []
    verified_count = 0
    
    print(f"Verifying {len(sample_keys)} random groups...")
    
    for key in sample_keys:
        files = true_dups[key]
        is_ident, diff = check_group(key, files)
        
        if is_ident:
            verified_count += 1
            # print(f"  [OK] {key}")
        else:
            print(f"  [FAIL] {key} - Differences found!")
            print(diff)
            discrepancies.append(key)
            
    print("-" * 50)
    print(f"Verification Results:")
    print(f"Groups Checked: {len(sample_keys)}")
    print(f"Verified Identical: {verified_count}")
    print(f"Discrepancies: {len(discrepancies)}")
    
    if discrepancies:
        print("WARNING: Some 'True Duplicates' are not valid!")
    else:
        print("SUCCESS: All sampled duplicates are content-identical.")

if __name__ == "__main__":
    main()
