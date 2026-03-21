import os
import json
import glob
import requests
import re
import random
import time
from bs4 import BeautifulSoup

DOWNLOADS_DIR = "downloads"
METADATA_PATTERN = "metadata_*.json"
BASE_URL = "https://chanrobles.com/cralaw/"
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]

def check_internal_consistency():
    print("=== Phase 1: Internal Consistency (Metadata vs Downloads) ===")
    print(f"{'Year':<6} | {'Meta':<6} | {'Files':<6} | {'Diff':<6} | {'Status':<10}")
    print("-" * 45)
    
    metadata_files = sorted(glob.glob(METADATA_PATTERN))
    total_meta = 0
    total_files = 0
    
    for meta_file in metadata_files:
        year = meta_file.replace("metadata_", "").replace(".json", "")
        
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                meta_count = len(data)
        except Exception as e:
            print(f"Error reading {meta_file}: {e}")
            continue

        # Count downloads for this year
        year_path = os.path.join(DOWNLOADS_DIR, str(year))
        file_count = 0
        if os.path.exists(year_path):
             for root, dirs, files in os.walk(year_path):
                for file in files:
                    if file.endswith(".json"):
                        file_count += 1
                        
        diff = meta_count - file_count
        status = "MATCH" if diff == 0 else "MISMATCH"
        
        # Only print non-zero diffs or every 10th year to save space, 
        # but user wants verification, so printing all mismatch is key.
        if diff != 0:
            print(f"{year:<6} | {meta_count:<6} | {file_count:<6} | {diff:<6} | {status:<10}")
        
        total_meta += meta_count
        total_files += file_count
        
    print("-" * 45)
    print(f"TOTAL  | {total_meta:<6} | {total_files:<6} | {total_meta-total_files:<6} |")
    print("\n")

def get_live_count(year, month):
    url = f"{BASE_URL}{year}{month}decisions.php"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return -1 # Error
            
        soup = BeautifulSoup(response.content, 'html.parser')
        # Regex from chanrobles_scraper.py
        pattern = re.compile(rf"{year}{month}decisions\.php\?id=\d+")
        links = soup.find_all('a', href=pattern)
        
        # Unique IDs
        ids = set()
        for link in links:
             href = link.get('href')
             try:
                case_id = href.split("id=")[1]
                ids.add(case_id)
             except: pass
        return len(ids)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return -1

def check_live_samples(samples=5):
    print(f"=== Phase 2: Live Spot Checks ({samples} Samples) ===")
    print("Fetching live data from chanrobles.com to verify counts...")
    print(f"{'Year':<6} | {'Month':<10} | {'Live':<6} | {'Local':<6} | {'Status':<10}")
    print("-" * 55)
    
    # Pick random years between 1901 and 2023 (exclude 2024 as known incomplete)
    valid_years = [y for y in range(1901, 2024)]
    
    for i in range(samples):
        year = random.choice(valid_years)
        month = random.choice(MONTHS)
        
        live_count = get_live_count(year, month)
        
        if live_count == -1:
            print(f"{year:<6} | {month:<10} | {'ERR':<6} | {'-':<6} | {'NET_ERR':<10}")
            continue
            
        # Count local
        local_count = 0
        month_path = os.path.join(DOWNLOADS_DIR, str(year), month)
        if os.path.exists(month_path):
            local_count = len(glob.glob(os.path.join(month_path, "*.json")))
            
        status = "MATCH" if live_count == local_count else "DIFF"
        print(f"{year:<6} | {month:<10} | {live_count:<6} | {local_count:<6} | {status:<10}")
        
        time.sleep(1) # Be polite

if __name__ == "__main__":
    check_internal_consistency()
    check_live_samples(5)
