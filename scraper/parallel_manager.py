import concurrent.futures
import subprocess
import os
import time
import argparse

# Configuration
YEAR_START = 1901
YEAR_END = 2024
MAX_WORKERS = 10
SCRAPER_SCRIPT = "chanrobles_scraper.py"
DOWNLOADER_SCRIPT = "download_decisions.py"

def process_year(year):
    """
    Runs the scraping pipeline for a specific year.
    1. Scrape Metadata -> metadata_{year}.json
    2. Download Decisions -> downloads/{year}/... (handled by downloader)
    """
    metadata_file = f"metadata_{year}.json"
    
    print(f"[Driver] Starting Year {year}...")
    
    # Step 1: Scrape Metadata
    # python chanrobles_scraper.py --year {year} --output {metadata_file}
    
    start_time = time.time()
    
    try:
        cmd_meta = ["python", SCRAPER_SCRIPT, "--year", str(year), "--output", metadata_file]
        # properly capture output to avoid cluttering main console too much, or let it stream?
        # Let's let it stream for visibility, but prefixing would be nice. 
        # For simplicity, we just run it.
        subprocess.check_call(cmd_meta)
        
    except subprocess.CalledProcessError as e:
        print(f"[Driver] Error scraping metadata for {year}: {e}")
        return year, False
        
    # Check if metadata file exists and has content
    if not os.path.exists(metadata_file) or os.path.getsize(metadata_file) < 5:
        print(f"[Driver] No metadata found for {year} or empty file.")
        # Cleanup empty file if exists
        # os.remove(metadata_file) 
        return year, True # Considered "Done" but empty
        
    # Step 2: Download Decisions
    # python download_decisions.py --metadata {metadata_file}
    
    try:
        cmd_down = ["python", DOWNLOADER_SCRIPT, "--metadata", metadata_file]
        subprocess.check_call(cmd_down)
    except subprocess.CalledProcessError as e:
        print(f"[Driver] Error downloading decisions for {year}: {e}")
        return year, False
        
    elapsed = time.time() - start_time
    print(f"[Driver] Finished Year {year} in {elapsed:.2f}s")
    
    # Optional: Delete metadata file to save space if needed? 
    # Or keep it for record. Keeping for now.
    
    return year, True

def main():
    parser = argparse.ArgumentParser(description="Parallel Scraper Manager")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Number of parallel workers")
    parser.add_argument("--start", type=int, default=YEAR_START, help="Start Year")
    parser.add_argument("--end", type=int, default=YEAR_END, help="End Year")
    
    args = parser.parse_args()
    
    years = list(range(args.start, args.end + 1))
    # Reverse order might be interesting (newest first)? Or oldest first? 
    # User didn't specify, but often newest is more valuable. 
    # Let's stick to chronological for "completeness".
    
    print(f"Starting Parallel Scraper with {args.workers} workers for years {args.start}-{args.end}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        # We submit all tasks
        future_to_year = {executor.submit(process_year, year): year for year in years}
        
        for future in concurrent.futures.as_completed(future_to_year):
            year = future_to_year[future]
            try:
                year, success = future.result()
                status = "Success" if success else "Failed"
                # print(f"Year {year} completed: {status}") 
            except Exception as exc:
                print(f"Year {year} generated an exception: {exc}")

    print("All years processed.")

if __name__ == "__main__":
    main()
