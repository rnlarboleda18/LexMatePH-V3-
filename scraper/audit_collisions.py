
import os
import json
import hashlib
import concurrent.futures
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
from convert_html_to_markdown import CaseConverter  # Re-use extraction logic

# Configuration
SC_SCRAPER_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper")
DOWNLOADS_DIR = SC_SCRAPER_DIR / "downloads"
REPORT_FILE = SC_SCRAPER_DIR / "collision_report.json"
MAX_WORKERS = 50

def compute_content_hash(soup):
    """
    Computes SHA256 hash of the text content to identify true duplicates.
    Normalizes whitespace to avoid false positives.
    """
    text = soup.get_text(separator=" ", strip=True)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def process_file_audit(file_path):
    """
    Extracts metadata and hash for a single file. (Standalone for Multiprocessing)
    """
    try:
        # Re-instantiate locally to ensure process safety
        converter = CaseConverter() 
        
        # Extract year and month from path for date fallback
        path_parts = Path(file_path).parts
        year = None
        month = None
        # Parsing: .../2018/may/389.html
        # Standard downloads structure: downloads/YEAR/MONTH/FILE
        if len(path_parts) >= 3:
            for part in path_parts:
                if part.isdigit() and len(part) == 4:
                    year = part
                    try:
                         # Month is usually the next part
                         idx = path_parts.index(part)
                         if idx + 1 < len(path_parts):
                             month = path_parts[idx+1]
                    except:
                        pass
                    break

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        soup = BeautifulSoup(content, "lxml")
        
        # Corrected Method Calls
        # extract_case_number(html_content, soup)
        case_number = converter.extract_case_number(content, soup)
        
        # extract_date(soup, year, month)
        date = converter.extract_date(soup, year, month)
        
        if not case_number or not date:
            return None
            
        case_key = f"{case_number}_{date}"
        file_hash = compute_content_hash(soup)
        
        return {
            "path": str(file_path),
            "key": case_key,
            "hash": file_hash,
            "size": len(content)
        }
    except Exception as e:
        return None

def main():
    print(f"Starting audit of {DOWNLOADS_DIR} with ProcessPoolExecutor...")
    
    # gather all html files
    all_files = list(DOWNLOADS_DIR.rglob("*.html"))
    print(f"Found {len(all_files)} items to scan.")
    
    results_by_key = defaultdict(list)
    processed_count = 0
    
    # Use ProcessPoolExecutor for CPU-bound parsing
    # Adjust max_workers for CPU cores (e.g. 10-16 for typical desktop)
    # Using 20 as a safe upper bound for desktop usage without stalling system
    with concurrent.futures.ProcessPoolExecutor(max_workers=20) as executor:
        # Submit all tasks
        # passing only path string to avoid pickling heavy objects
        future_to_file = {executor.submit(process_file_audit, f): f for f in all_files}
        
        for future in concurrent.futures.as_completed(future_to_file):
            processed_count += 1
            if processed_count % 2500 == 0:
                print(f"Scanned {processed_count}/{len(all_files)} files...")
                
            result = future.result()
            if result:
                results_by_key[result["key"]].append(result)

    print("Scan complete. Analyzing collisions...")
    
    # Analyze Collisions
    distinct_collisions = {}
    true_duplicates = {}
    unique_cases = 0
    
    for key, file_list in results_by_key.items():
        if len(file_list) == 1:
            unique_cases += 1
            continue
            
        # We have multiple files for this key (Collision)
        hashes = set(f["hash"] for f in file_list)
        
        if len(hashes) > 1:
            # Distinct Content -> Separate Opinions or collisions!
            distinct_collisions[key] = file_list
        else:
            # Identical Content -> True Duplicates
            true_duplicates[key] = file_list

    # Generate Report
    report = {
        "summary": {
            "total_files_scanned": processed_count,
            "unique_case_keys": len(results_by_key),
            "single_file_cases": unique_cases,
            "collision_groups_total": len(distinct_collisions) + len(true_duplicates),
            "distinct_collision_groups": len(distinct_collisions),
            "true_duplicate_groups": len(true_duplicates)
        },
        "distinct_collisions": distinct_collisions,
        # "true_duplicates": true_duplicates # Optional: exclude to save space if needed
    }
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print("\nAudit Final Results:")
    print(f"Total Scanned: {processed_count}")
    print(f"Unique Case Keys: {len(results_by_key)}")
    print(f"Distinct Collision Groups (Target for Recovery): {len(distinct_collisions)}")
    print(f"True Duplicate Groups (Safe to ignore): {len(true_duplicates)}")
    print(f"Report saved to: {REPORT_FILE}")

if __name__ == "__main__":
    main()
