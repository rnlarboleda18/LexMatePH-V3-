"""
Test conversion of two specific cases with G.R. No. 237428
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from convert_html_to_markdown import CaseConverter

# Files to convert
HTML_FILES = [
    Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2024\may\139.html"),
    Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2024\april\101.html"),
]
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\Converted MD")

def main():
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create converter
    converter = CaseConverter()
    
    print("="*80)
    print(f"Converting TWO cases with G.R. No. 237428 references")
    print("="*80)
    print(f"Output: {OUTPUT_DIR}\n")
    
    # Process each file
    for html_file in HTML_FILES:
        if not html_file.exists():
            print(f"SKIP: File not found: {html_file}")
            continue
            
        print(f"\nProcessing: {html_file.name}")
        converter.process_file(html_file)
    
    print("\n" + "="*80)
    print("CONVERSION STATS")
    print("="*80)
    print(f"Processed: {converter.stats['processed']}")
    print(f"Success:   {converter.stats['success']}")
    print(f"Failed:    {converter.stats['failed']}")
    print(f"Skipped:   {converter.stats['skipped']}")
    
    if converter.stats['errors']:
        print("\nErrors:")
        for error in converter.stats['errors']:
            print(f"  - {error}")
    
    print(f"\nConverted files saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    # Monkey-patch the OUTPUT_DIR
    import convert_html_to_markdown
    convert_html_to_markdown.OUTPUT_DIR = OUTPUT_DIR
    convert_html_to_markdown.MANIFEST_FILE = OUTPUT_DIR / "conversion_manifest.json"
    
    main()
