import os
import glob
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Config
HTML_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html"
OUTPUT_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md_reprocessed"
CONVERTER_SCRIPT = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\scraper\lawphil_converter_html_to_md.py"

def convert_file(html_path):
    try:
        # Construct output path
        base_name = os.path.basename(html_path)
        name_no_ext = os.path.splitext(base_name)[0]
        output_path = os.path.join(OUTPUT_DIR, f"{name_no_ext}.md")
        
        # Run converter
        subprocess.run(["python", CONVERTER_SCRIPT, html_path, OUTPUT_DIR], check=True, capture_output=True)
        print(f"Converted: {base_name}")
        return True
    except Exception as e:
        print(f"Failed {html_path}: {e}")
        return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Gather files - Recursive search
    html_files = glob.glob(os.path.join(HTML_DIR, "**", "*.html"), recursive=True)
    print(f"Found {len(html_files)} HTML files to convert.")

    # Run in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(convert_file, html_files))

    print(f"Finished. Success: {results.count(True)}/{len(results)}")

if __name__ == "__main__":
    main()
