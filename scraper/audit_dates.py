import os
import re
import random
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")

def parse_filename_date(fname):
    # Format: G.R. No. 12345_Month_DD_YYYY.md
    # Regex for ending: _([A-Z][a-z]+)_(\d{2})_(\d{4})\.md
    match = re.search(r'_([A-Z][a-z]+)_(\d{2})_(\d{4})\.md$', fname)
    if match:
        return f"{match.group(1)} {match.group(2)}, {match.group(3)}"
    return None

def extract_header_date(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = [f.readline().strip() for _ in range(20)]
    except:
        return None

    # Regex for strict date: Month DD, YYYY
    # Must be reasonably standalone or part of a header
    date_pattern = re.compile(r'([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})')
    
    for line in lines:
        if not line: continue
        # remove markdown chars
        clean = line.replace('#', '').replace('*', '').strip()
        
        matches = date_pattern.findall(clean)
        for match in matches:
            month, day, year = match
            # Validate month
            if month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]:
                return f"{month} {day}, {year}"
    return None

def audit_dates():
    files = list(ROOT_DIR.rglob("*.md"))
    if not files:
        print("No files found.")
        return

def parse_date(date_str):
    if not date_str: return None
    # Normalize spaces
    date_str = " ".join(date_str.split())
    try:
        return datetime.strptime(date_str, "%B %d, %Y")
    except:
        return None

def audit_dates():
    files = list(ROOT_DIR.rglob("*.md"))
    if not files:
        print("No files found.")
        return

    sample = random.sample(files, min(len(files), 100)) # Increase sample size
    
    print(f"{'FILENAME':<60} | {'FILE_DATE':<20} | {'HEADER_DATE':<20} | {'STATUS'}")
    print("-" * 120)
    
    mismatch_count = 0
    real_mismatch_count = 0
    
    for p in sample:
        f_date_str = parse_filename_date(p.name)
        h_date_str = extract_header_date(p)
        
        f_dt = parse_date(f_date_str)
        h_dt = parse_date(h_date_str)
        
        if f_dt and h_dt:
            if f_dt != h_dt:
                status = "MISMATCH"
                real_mismatch_count += 1
            else:
                status = "OK"
        elif not h_date_str:
             status = "NO HEADER"
        else:
             status = "PARSE ERROR"
             
        if status == "MISMATCH":
             print(f"{p.name[:58]:<60} | {str(f_date_str):<20} | {str(h_date_str):<20} | {status}")

    print(f"\nAudit Sample: {len(sample)}")
    print(f"Real Mismatches: {real_mismatch_count}")

if __name__ == "__main__":
    audit_dates()
