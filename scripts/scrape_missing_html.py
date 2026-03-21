import os
import csv
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
INPUT_CSV = "data/missing_in_db_report.csv"
OUTPUT_DIR = "data/sc_elib_html"
MAX_WORKERS = 10

def fetch_html(url, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 404:
                print(f"404 Not Found: {url}")
                return None
            else:
                # Server error, retry
                time.sleep(1)
        except Exception as e:
            # Network error, retry
            time.sleep(1)
            
    print(f"Failed to fetch {url} after {retries} attempts.")
    return None

def process_row(row):
    elib_id = row.get('elib_id')
    url = row.get('url')
    
    if not elib_id or not url:
        return False

    output_path = os.path.join(OUTPUT_DIR, f"{elib_id}.html")
    
    if os.path.exists(output_path):
        return True # Skip
        
    content = fetch_html(url)
    if content:
        with open(output_path, 'wb') as f:
            f.write(content)
        return True
    return False

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Input file not found: {INPUT_CSV}")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    # Read Rows
    rows = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    print(f"Starting scrape for {total} items...")

    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_row, row): row for row in rows}
        
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0:
                print(f"Progress: {completed}/{total} ({(completed/total)*100:.1f}%)", end='\r')
    
    print(f"\nCompleted scraping. Check {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
