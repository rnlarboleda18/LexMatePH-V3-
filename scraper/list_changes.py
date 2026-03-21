import os
import re
from pathlib import Path
from datetime import datetime
import concurrent.futures
import json
from bs4 import BeautifulSoup
from lawphil_convert_html_to_markdown import CaseConverter

# Directories
HTML_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
MD_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")

def parse_md_filename(path):
    # G.R. No. L-1503_November_16_1903.md
    # Regex for ending: _([A-Z][a-z]+)_(\d{2})_(\d{4})\.md
    # And getting the case number part
    match = re.search(r'^(.*)_([A-Z][a-z]+)_(\d{2})_(\d{4})\.md$', path.name)
    if match:
        case_no = match.group(1).replace('_', '-') # Normalize underscores to hyphens? Or just keep generic
        # Case number in filename uses underscores for non-safe chars.
        # But let's keep it as is for map key if possible.
        # Wait, HTML extraction yields "G.R. No. L-1503".
        # MD Filename: "G.R. No. L-1503".
        # Safe version: replced chars with _.
        
        date_str = f"{match.group(2)} {match.group(3)}, {match.group(4)}"
        try:
            dt = datetime.strptime(date_str, "%B %d, %Y")
            return case_no, dt.strftime("%Y-%m-%d")
        except:
            return None, None
    return None, None

def get_html_info(html_path):
    converter = CaseConverter()
    try:
        with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # We need the Case Number and Date as the Converter finds it
        head_meta = converter.extract_metadata_from_head(content)
        soup = BeautifulSoup(content, 'html.parser')
        # We must clean DOM to match converter behavior!
        soup = converter.clean_soup_dom(soup) # Important? Yes.
        body_info = converter.extract_header_info_from_body(soup)
        
        case_number = head_meta.get('case_number') or body_info.get('case_number')
        date_str = body_info.get('date')
        
        # Fallback date logic from converter
        if not date_str:
             if 'date' in head_meta: date_str = head_meta['date']
             # Path fallback ignored for now as it usually yields Jan 01
        
        # Fallback case number
        if not case_number:
            # logic... we can skip or use filename
            pass
            
        # Normalize date
        final_date = "Unknown"
        if date_str:
            try:
                clean_date = date_str.replace(",", "")
                dt = datetime.strptime(clean_date, "%B %d %Y")
                final_date = dt.strftime("%Y-%m-%d")
            except:
                pass
                
        # Normalize case number for comparison key
        # Converter uses: safe_case_number = re.sub(r'[<>:"/\\|?*]', '_', str(case_number)).strip()
        safe_case = "Unknown"
        if case_number:
            safe_case = re.sub(r'[<>:"/\\|?*]', '_', str(case_number)).strip()
            
        return safe_case, final_date
        
    except Exception as e:
        return None, None

def scan_mds():
    md_map = {} # {safe_case_number: date_str}
    print("Scanning MD files...")
    files = list(MD_DIR.rglob("*.md"))
    for f in files:
        case, date = parse_md_filename(f)
        if case and date:
            md_map[case] = date # If duplicate, last wins (should be consistent usually)
    return md_map

def find_changes():
    # 1. Get current state (Corrected)
    md_map = scan_mds()
    print(f"Loaded {len(md_map)} MD entries.")
    
    # 2. Get original state (Simulated)
    html_files = list(HTML_DIR.rglob("*.html"))
    print(f"Scanning {len(html_files)} HTML files with 50 workers...")
    
    changes = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(get_html_info, p): p for p in html_files}
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if i % 5000 == 0:
                print(f"Processed {i} HTMLs...")
                
            safe_case, html_date = future.result()
            
            if safe_case and safe_case in md_map:
                md_date = md_map[safe_case]
                
                # Compare
                # Ignore if html_date is Unknown (converter likely used fallback path date)
                if html_date != "Unknown" and html_date != md_date:
                    changes.append(f"{safe_case} (Old: {html_date} -> New: {md_date})")
                    
    print("\n" + "="*50)
    print(f"Found {len(changes)} Case Date Corrections:")
    for c in sorted(changes):
        print(c)
        
    # Save to file
    with open("corrected_cases_list.txt", "w", encoding='utf-8') as f:
        for c in sorted(changes):
            f.write(c + "\n")
            
    print(f"List saved to corrected_cases_list.txt")

if __name__ == "__main__":
    find_changes()
