
import json
import os
from pathlib import Path

# Config
DOWNLOADS_DIR = Path("C:/Users/rnlar/.gemini/antigravity/scratch/sc_scraper/downloads")
MANIFEST_FILE = Path("C:/Users/rnlar/.gemini/antigravity/scratch/Converted MD/conversion_manifest.json")
OUTPUT_LIST = Path("C:/Users/rnlar/.gemini/antigravity/scratch/sc_scraper/retry_list.txt")

def generate_retry_list():
    print("Loading manifest...")
    processed_paths = set()
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            for entry in manifest:
                # Normalize path separators
                p = str(Path(entry['source_html']).absolute())
                processed_paths.add(p)
    
    print(f"Manifest contains {len(processed_paths)} processed files.")
    
    print("Scanning 1901-1974 downloads...")
    files_to_retry = []
    total_files = 0
    
    # Range 1901 to 1974
    for year in range(1901, 1975):
        year_dir = DOWNLOADS_DIR / str(year)
        if year_dir.exists():
            for root, dirs, files in os.walk(year_dir):
                for file in files:
                    if file.endswith('.html'):
                        total_files += 1
                        file_path = Path(root) / file
                        normalization_path = str(file_path.absolute())
                        
                        if normalization_path not in processed_paths:
                            files_to_retry.append(normalization_path)
    
    print(f"Total files in range: {total_files}")
    print(f"Files to retry (Failed + Skipped): {len(files_to_retry)}")
    
    # Save list
    with open(OUTPUT_LIST, 'w', encoding='utf-8') as f:
        for p in files_to_retry:
            f.write(p + "\n")
            
    print(f"Retry list saved to {OUTPUT_LIST}")

if __name__ == "__main__":
    generate_retry_list()
