import os
import sys
from pathlib import Path

# Fix import path for lawphil_convert_html_to_markdown
SCRIPTS_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper")
sys.path.append(str(SCRIPTS_DIR))

try:
    from lawphil_convert_html_to_markdown import CaseConverter
except ImportError:
    print("Error: Could not import CaseConverter from lawphil_convert_html_to_markdown.py")
    sys.exit(1)

# --- CONFIGURATION ---
HTML_SCRAPED_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html_scraped")
MD_FIXED_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md_fixed")
MAX_WORKERS = 10 # Upping workers for speed

def main():
    print(f"Starting conversion of rescraped HTML in {HTML_SCRAPED_DIR}...")
    MD_FIXED_DIR.mkdir(parents=True, exist_ok=True)
    
    converter = CaseConverter(output_dir=MD_FIXED_DIR)
    
    # Collect all HTML files
    html_files = []
    for root, dirs, files in os.walk(HTML_SCRAPED_DIR):
        for f in files:
            if f.endswith(".html"):
                html_files.append(Path(root) / f)
    
    print(f"Found {len(html_files)} HTML files to convert.")
    
    if not html_files:
        print("No HTML files found to convert. Exiting.")
        return

    # run_full_conversion expects a path to a file containing the list of paths
    temp_list_path = Path("rescraped_html_fixed_list.txt")
    with open(temp_list_path, 'w', encoding='utf-8') as f:
        for p in html_files:
            f.write(f"{p}\n")
    
    # Run conversion
    converter.run_full_conversion(workers=MAX_WORKERS, file_list=str(temp_list_path), overwrite=True)
    
    if temp_list_path.exists():
        os.remove(temp_list_path)
    
    print(f"\nConversion Complete.")
    print(f"Stats: {converter.stats}")
    print(f"Markdown files saved to {MD_FIXED_DIR}")

if __name__ == "__main__":
    main()
