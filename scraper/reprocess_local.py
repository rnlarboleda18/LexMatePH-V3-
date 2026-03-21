import os
import json
import glob
from concurrent.futures import ThreadPoolExecutor
from content_parser import parse_decision_content

DOWNLOADS_DIR = "downloads"
WORKERS = 20

def reprocess_file(html_path):
    try:
        # Determine paths
        json_path = html_path.replace(".html", ".json")
        
        # We need the original metadata (case_number, year) from the existing JSON
        # If JSON doesn't exist, we can't fully reconstruct it easily without looking up metadata again.
        # But we assume the scrape was successful, so JSON exists.
        
        if not os.path.exists(json_path):
            # print(f"Skipping {html_path}, no corresponding JSON found.")
            return
            
        with open(json_path, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
            
        # Parse content from HTML
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        parsed = parse_decision_content(html_content)
        new_text = parsed.get("main_text", "")
        
        # Check if text changed (optimization/logging only)
        # old_len = len(current_data.get("main_text", ""))
        # new_len = len(new_text)
        
        # Update Data
        current_data["main_text"] = new_text
        
        # Save back
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, indent=4, ensure_ascii=False)
            
        return True
    except Exception as e:
        # print(f"Error processing {html_path}: {e}")
        return False

def find_html_files():
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        for file in files:
            if file.endswith(".html"):
                yield os.path.join(root, file)

def main():
    print("Indexing all files for parallel processing...", flush=True)
    # Collect all files first to avoid generator contention in threads
    all_files = list(find_html_files())
    total_files = len(all_files)
    print(f"Found {total_files} files. Starting 30-worker parallel pool...", flush=True)
    
    processed_count = 0
    # Parallel Mode: 30 Workers
    with ThreadPoolExecutor(max_workers=30) as executor:
        # We iterate over the results as they complete
        for _ in executor.map(reprocess_file, all_files):
            processed_count += 1
            if processed_count % 500 == 0:
                print(f"Processed {processed_count}/{total_files} files...", flush=True)
                
    print(f"Reprocessing completed. Total: {processed_count}", flush=True)

if __name__ == "__main__":
    main()
