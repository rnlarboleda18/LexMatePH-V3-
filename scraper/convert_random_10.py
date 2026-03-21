"""
Quick script to convert 10 random HTML files to markdown
Saves output to Converted MD directory
"""

import sys
from pathlib import Path

# Add the sc_scraper directory to the path to import the converter
sys.path.insert(0, str(Path(__file__).parent))

from convert_html_to_markdown import CaseConverter
import random
import os

# Override directories
DOWNLOADS_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads")
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\Converted MD")
MANIFEST_FILE = OUTPUT_DIR / "conversion_manifest.json"

def main():
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create converter instance
    converter = CaseConverter()
    
    # Collect all HTML files
    print("Scanning for HTML files...")
    all_files = []
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        for file in files:
            if file.endswith('.html'):
                all_files.append(Path(root) / file)
    
    print(f"Found {len(all_files)} total HTML files")
    
    # Select 10 random files
    if len(all_files) > 10:
        selected_files = random.sample(all_files, 10)
    else:
        selected_files = all_files[:10]
    
    print(f"\nConverting {len(selected_files)} random files...\n")
    
    # Process each file
    for html_path in selected_files:
        # Modify the output directory for this conversion
        converter.process_file(html_path)
    
    print("\n" + "=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"Processed: {converter.stats['processed']}")
    print(f"Success:   {converter.stats['success']}")
    print(f"Failed:    {converter.stats['failed']}")
    print(f"Skipped:   {converter.stats['skipped']}")
    print(f"\nMarkdown files saved to: {OUTPUT_DIR}")
    
    if converter.stats['errors']:
        print(f"\nErrors encountered:")
        for error in converter.stats['errors']:
            print(f"  - {error}")

if __name__ == "__main__":
    # Monkey-patch the OUTPUT_DIR in the converter module
    import convert_html_to_markdown
    convert_html_to_markdown.OUTPUT_DIR = OUTPUT_DIR
    convert_html_to_markdown.MANIFEST_FILE = MANIFEST_FILE
    
    main()
