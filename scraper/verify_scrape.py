import os
import json
import glob

DOWNLOADS_DIR = "downloads"
START_YEAR = 1901
END_YEAR = 2024

def verify_scrape():
    print(f"Verifying scrape results in {DOWNLOADS_DIR}...")
    print(f"{'Year':<6} | {'Files':<8} | {'Status':<10}")
    print("-" * 30)

    total_files = 0
    missing_years = []
    low_count_years = []

    for year in range(START_YEAR, END_YEAR + 1):
        year_path = os.path.join(DOWNLOADS_DIR, str(year))
        
        if not os.path.exists(year_path):
            print(f"{year:<6} | {'0':<8} | {'MISSING':<10}")
            missing_years.append(year)
            continue
            
        # Count JSON files recursively in year folder (Year/Month/ID.json)
        # Using glob might be slow depending on depth, but structure is Year/Month/file.json
        # Faster to walk
        file_count = 0
        for root, dirs, files in os.walk(year_path):
            for file in files:
                if file.endswith(".json"):
                    file_count += 1
        
        status = "OK"
        if file_count == 0:
            status = "EMPTY"
            missing_years.append(year) # Technially exists but empty
        elif file_count < 10:
            status = "LOW" # Warning for modern years, expected for 1901
            low_count_years.append(year)
            
        print(f"{year:<6} | {file_count:<8} | {status:<10}")
        total_files += file_count

    print("-" * 30)
    print(f"Total Decisions Scraped: {total_files}")
    
    if missing_years:
        print(f"\nWARNING: The following years are MISSING or EMPTY: {missing_years}")
        
    if low_count_years:
        print(f"\nNOTE: The following years have < 10 decisions: {low_count_years}")
        
    # Check sample integrity
    print("\nChecking sample integrity (random file)...")
    try:
        sample_year = 2000
        sample_files = glob.glob(os.path.join(DOWNLOADS_DIR, str(sample_year), "**", "*.json"), recursive=True)
        if sample_files:
            with open(sample_files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Sample ({sample_files[0]}):")
                print(f"  Case No: {data.get('case_number')}")
                print(f"  Year: {data.get('year')}")
                len_text = len(data.get('main_text', ''))
                print(f"  Text Length: {len_text} chars")
                if len_text > 100:
                    print("  Status: VALID CONTENT")
                else:
                    print("  Status: POTENTIALLY EMPTY CONTENT")
    except Exception as e:
        print(f"Sample check failed: {e}")

if __name__ == "__main__":
    verify_scrape()
