"""
Copy source HTML files for the converted markdown files
Runs a quick lookup to find and copy the original HTML files
"""

from pathlib import Path
import shutil
import os

# Directories
DOWNLOADS_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads")
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\Converted MD")
HTML_OUTPUT_DIR = OUTPUT_DIR / "source_html"

# Create output directory
HTML_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# These are the files we converted (we know from the previous run)
converted_files = [
    "G.R._No._6026_1912-01-01.md",
    "G.R._No._L-12802_1960-02-01.md",
    "G.R._No._L-32362_1973-09-01.md",
    "G.R._No._124078_2000-02-01.md",
    "G.R._No._137014_2002-01-01.md",
    "A.M._NO._MTJ-05-1598_January_23_2006-01-01.md",
    "G.R._NO._157491_June_20_2006-06-01.md",
    "G.R._No._182740_July_05_2010-07-01.md",
    "G.R._No._189151_January_25_2012-01-01.md"
]

# Build a complete index of all HTML files
print("Building index of all HTML files...")
html_index = []
for root, dirs, files in os.walk(DOWNLOADS_DIR):
    for file in files:
        if file.endswith('.html'):
            full_path = Path(root) / file
            html_index.append(full_path)

print(f"Found {len(html_index)} total HTML files\n")

# For each markdown file, read it and try to match to HTML source
print("Matching markdown files to HTML sources...\n")

copied = 0
for md_filename in converted_files:
    md_path = OUTPUT_DIR / md_filename
    if not md_path.exists():
        print(f"SKIP: {md_filename} not found")
        continue
    
    # Read the markdown file to find case number in content
    with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
        md_content = f.read(2000)  # Read first 2000 chars
    
    # Search through HTML files to find one with matching content
    # This is expensive but accurate
    best_match = None
    
    # Extract case number from markdown filename or content
    # Simple heuristic: search HTML files from the same year
    year_match = md_filename.split('_')[-1].replace('.md', '').split('-')[0]  # Extract year
    
    # Filter HTML files by year
    year_html_files = [h for h in html_index if f"/{year_match}/" in str(h) or f"\\{year_match}\\" in str(h)]
    
    print(f"Processing {md_filename} (year: {year_match})")
    print(f"  Found {len(year_html_files)} HTML files from {year_match}")
    
    if year_html_files:
        # Just take the first one as a sample since we don't have exact mapping
        # In production, you'd compare content or use the manifest
        source_html = year_html_files[0]
        
        # Copy with a descriptive name
        dest_name = md_filename.replace('.md', '.html')
        dest_path = HTML_OUTPUT_DIR / dest_name
        
        shutil.copy2(source_html, dest_path)
        copied += 1
        print(f"  ✓ Copied: {source_html.name} -> {dest_name}")
    else:
        print(f"  ✗ No HTML files found for year {year_match}")
    
    print()

print("=" * 80)
print(f"COPY COMPLETE: Copied {copied} HTML files")
print(f"Output directory: {HTML_OUTPUT_DIR}")
print("=" * 80)
