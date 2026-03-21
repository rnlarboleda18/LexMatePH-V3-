import requests
from bs4 import BeautifulSoup
import csv
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Range defined by user
START_ID = 40392
END_ID = 70041

BASE_URL = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{}"
OUTPUT_FILE = "data/sc_elib_metadata.csv"

# Regex patterns
# Pattern for "G.R. No. XXXXX, Month DD, YYYY" inside brackets usually
# Or simplified: Case No... Date
DATE_PATTERN = re.compile(r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})")
CASE_NO_PATTERN = re.compile(r"(G\.R\.\s+No\.\s+[\w\-\.]+)", re.IGNORECASE)

def fetch_metadata(doc_id):
    url = BASE_URL.format(doc_id)
    response = None
    
    # 1. Network Request with Retry
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 404:
                return None
            if response.status_code == 200:
                break
        except Exception:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return None
            
    if not response or response.status_code != 200:
        return None

    # 2. Parse Content
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        case_no = "NULL"
        date = "NULL"
        title = "NULL"
        
        # Title from <title>
        if soup.title:
            title = soup.title.string.replace(" - Supreme Court E-Library", "").strip()

        # Case No and Date from <h2>
        h2_tags = soup.find_all('h2')
        header_text = ""
        
        for h2 in h2_tags:
            text = h2.get_text().strip()
            if text.startswith("[") and text.endswith("]"):
                header_text = text
                break
        
        if header_text:
            inner = header_text.strip("[] ").strip()
            
            # Date
            dt_match = DATE_PATTERN.search(inner)
            if dt_match:
                date = dt_match.group(1)
            
            # Case No
            cn_match = CASE_NO_PATTERN.search(inner)
            if cn_match:
                case_no = cn_match.group(1)
            else:
                parts = inner.split(",")
                if len(parts) >= 2:
                    case_no = parts[0].strip()

        return {
            "elib_id": doc_id,
            "case_number": case_no,
            "date": date, 
            "title": title,
            "url": url
        }

    except Exception:
        return None

def main():
    # Check if file exists to resume
    start_id = START_ID
    mode = 'w'
    
    if os.path.exists(OUTPUT_FILE):
        print("Output file exists. Appending...")
        mode = 'a'
        # Optional: Read last ID to resume? 
        # For now, simplistic resume logic later.
    else:
        # write header
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["elib_id", "case_number", "date", "title", "url"])
            writer.writeheader()

    print(f"Scraping IDs {START_ID} to {END_ID}...")
    
    with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["elib_id", "case_number", "date", "title", "url"])
        
        max_workers = 10
        # Chunking to manage memory/writes
        chunk_size = 100
        
        # Create full range
        all_ids = list(range(START_ID, END_ID + 1))
        
        total = len(all_ids)
        processed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # submit all? might be too many. Batch submission.
            for i in range(0, total, chunk_size):
                batch_ids = all_ids[i : i + chunk_size]
                futures = {executor.submit(fetch_metadata, doc_id): doc_id for doc_id in batch_ids}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        writer.writerow(result)
                        # print(f"Scraped {result['elib_id']}")
                    processed += 1
                
                f.flush() # Ensure write to disk
                print(f"Progress: {processed}/{total} ({processed/total:.1%})", end='\r')

    print("\nScraping complete.")

if __name__ == "__main__":
    main()
