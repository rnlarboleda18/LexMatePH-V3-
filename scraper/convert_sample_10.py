
import os
import random
import sys
from pathlib import Path

# Fix import path
sys.path.append(str(Path(__file__).parent))

from lawphil_convert_html_to_markdown import CaseConverter

def convert_samples():
    html_dir = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
    md_dir = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")
    
    # Ensure output exists
    md_dir.mkdir(parents=True, exist_ok=True)
    
    print("Listing all HTML files...")
    all_files = list(html_dir.rglob("*.html"))
    
    if not all_files:
        print("No HTML files found!")
        return

    print(f"Found {len(all_files)} files.")
    
    # Filter out potential index files if any remain
    valid_files = [f for f in all_files if "juri" not in f.name and "pdf" not in f.name]
    
    samples = random.sample(valid_files, min(10, len(valid_files)))
    
    print(f"Selected {len(samples)} samples:")
    for s in samples:
        print(f" - {s.name}")
        
    converter = CaseConverter(output_dir=md_dir)
    
    print("\nStarting conversion...")
    for html_path in samples:
        try:
            result = converter.process_file(html_path, overwrite=True)
            status = result.get('status', 'unknown')
            print(f"[{status}] {html_path.name}")
            if status == 'failed':
                print(f"Error: {result.get('error')}")
        except Exception as e:
            print(f"CRITICAL ERROR on {html_path.name}: {e}")

if __name__ == "__main__":
    convert_samples()
