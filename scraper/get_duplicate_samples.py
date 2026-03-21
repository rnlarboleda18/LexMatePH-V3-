
import concurrent.futures
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
import hashlib
from convert_html_to_markdown import CaseConverter

SC_SCRAPER_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper")
DOWNLOADS_DIR = SC_SCRAPER_DIR / "downloads"

def compute_content_hash(soup):
    text = soup.get_text(separator=" ", strip=True)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def process_file_audit(file_path):
    try:
        converter = CaseConverter()
        
        # Extract year/month from path for date logic (if needed)
        path_parts = Path(file_path).parts
        year = None
        month = None
        if len(path_parts) >= 3:
            for part in path_parts:
                if part.isdigit() and len(part) == 4:
                    year = part
                    try:
                         idx = path_parts.index(part)
                         if idx + 1 < len(path_parts):
                             month = path_parts[idx+1]
                    except:
                        pass
                    break

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        soup = BeautifulSoup(content, "lxml")
        
        # Use existing extraction logic
        case_number = converter.extract_case_number(content, soup)
        date = converter.extract_date(soup, year, month)
        
        if not case_number or not date:
            return None
            
        case_key = f"{case_number}_{date}"
        file_hash = compute_content_hash(soup)
        
        return {
            "path": str(file_path),
            "key": case_key,
            "hash": file_hash
        }
    except Exception:
        return None

def main():
    print("Scanning for duplicates...")
    all_files = list(DOWNLOADS_DIR.rglob("*.html"))
    
    # We need to find groups. We can't stop early easily unless we track keys seen.
    # But ProcessPool is unordered.
    # We'll run a quick scan.
    
    results_by_key = defaultdict(list)
    found_groups = 0
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=20) as executor:
        future_to_file = {executor.submit(process_file_audit, f): f for f in all_files}
        
        for future in concurrent.futures.as_completed(future_to_file):
            result = future.result()
            if result:
                results_by_key[result["key"]].append(result)
                
                # Check if we have a duplicate group here
                if len(results_by_key[result["key"]]) > 1:
                    # check if hash is identical
                    group = results_by_key[result["key"]]
                    hashes = set(f["hash"] for f in group)
                    if len(hashes) == 1:
                        # Found a true duplicate group!
                        # We can print it immediately
                        pass

    # Process results
    duplicate_groups = []
    for key, file_list in results_by_key.items():
        if len(file_list) > 1:
            hashes = set(f["hash"] for f in file_list)
            if len(hashes) == 1:
                duplicate_groups.append(file_list)
                if len(duplicate_groups) >= 2:
                    break
    
    print(f"\nFound {len(duplicate_groups)} duplicate groups (stopped early if >= 2).")
    
    for i, group in enumerate(duplicate_groups):
        print(f"\n--- Sample Duplicate Pair #{i+1} ---")
        print(f"Case Key: {group[0]['key']}")
        print(f"Content Hash: {group[0]['hash']}")
        print("Files:")
        for f in group:
            print(f"  {f['path']}")

if __name__ == "__main__":
    main()
