from lawphil_convert_html_to_markdown import CaseConverter
from pathlib import Path
import random
import os

HTML_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
MD_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\MD\lawphil")

def run_test():
    converter = CaseConverter()
    
    # Get all year directories
    years = [d for d in HTML_DIR.iterdir() if d.is_dir() and d.name.isdigit()]
    years.sort(key=lambda x: int(x.name), reverse=True)
    
    years.sort(key=lambda x: int(x.name), reverse=True)
    print(f"DEBUG: Years to process: {[y.name for y in years]}")
    import sys
    sys.stdout.flush()
    
    print(f"Found {len(years)} years.")
    
    for year_dir in years:
        year = year_dir.name
        files = list(year_dir.glob("*.html"))
        if not files: continue
        
        # Pick 1 random file
        target_file = random.choice(files)
        
        print(f"Converting {year}: {target_file.name}")
        
        # Provide fallback metadata
        start_date = f"{year}-01-01"
        result = converter.process_file(target_file, metadata={'date': start_date}, overwrite=True)
        
        if result['status'] == 'success':
            print(f"  -> Saved to {result['entry']['filename']}")
        elif result['status'] == 'skipped':
            print(f"  -> Skipped: {result.get('error')}")
        else:
            print(f"  -> Failed: {result.get('error')}")

if __name__ == "__main__":
    run_test()
