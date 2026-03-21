"""
Test conversion of specific case: G.R. No. 237428
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from convert_html_to_markdown import CaseConverter

# Files
HTML_FILE = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2024\may\139.html")
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\Converted MD")

def main():
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create converter
    converter = CaseConverter()
    
    print("="*80)
    print(f"Converting G.R. No. 237428")
    print("="*80)
    print(f"Source: {HTML_FILE}")
    print(f"Output: {OUTPUT_DIR}\n")
    
    # Process the file
    converter.process_file(HTML_FILE)
    
    print("\n" + "="*80)
    print("CONVERSION STATS")
    print("="*80)
    print(f"Processed: {converter.stats['processed']}")
    print(f"Success:   {converter.stats['success']}")
    print(f"Failed:    {converter.stats['failed']}")
    
    if converter.stats['errors']:
        print("\nErrors:")
        for error in converter.stats['errors']:
            print(f"  - {error}")

if __name__ == "__main__":
    # Monkey-patch the OUTPUT_DIR
    import convert_html_to_markdown
    convert_html_to_markdown.OUTPUT_DIR = OUTPUT_DIR
    convert_html_to_markdown.MANIFEST_FILE = OUTPUT_DIR / "conversion_manifest.json"
    
    main()
