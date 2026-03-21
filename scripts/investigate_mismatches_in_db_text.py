import os
import re
import json
import psycopg
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Config
DATA_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\sc_elib_md")
DB_CONFIG_PATH = "api/local.settings.json"

def get_db_connection_string():
    try:
        with open(DB_CONFIG_PATH, "r") as f:
            settings = json.load(f)
            return settings["Values"]["DB_CONNECTION_STRING"]
    except Exception as e:
        print(f"Error loading settings: {e}")
        return None

def normalize_key(s):
    if not s: return ""
    return re.sub(r'[\W_]+', '', s).lower()

# Load DB Cache (Date -> List of (id, case_number, full_text_md))
# NOTE: fetching full_text_md might be heavy, so let's do it only for specific dates we find interesting
# Actually, better strategy:
# 1. Scan files, find the "CN Mismatch" ones.
# 2. Collect their (Date, MD_CaseNo).
# 3. For each unique Date in that set, fetch DB records (id, case_number, full_text_md).
# 4. Check matches.

def parse_markdown_header(filepath):
    try:
        full_text = Path(filepath).read_text(encoding='utf-8')
        # Regex from previous step
        header_match = re.search(r'##\s*\[\s*(.*?),\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s*\]', full_text[:1000])
        
        if header_match:
            cnum_raw = header_match.group(1)
            date_raw = header_match.group(2)
            try:
                dt = datetime.strptime(date_raw, "%B %d, %Y")
                date_str = dt.strftime("%Y-%m-%d")
                return {
                    "cnum": normalize_key(cnum_raw),
                    "raw_cnum": cnum_raw,
                    "date": date_str
                }
            except:
                pass
        return None
    except:
        return None

def investigate():
    conn_str = get_db_connection_string()
    if not conn_str: return

    # 1. Identify Mismatches first (using lightweight cache)
    print("Loading lightweight DB map for filtering...")
    db_dates = set()
    db_cnums = {} # Date -> set of normalized Case Numbers
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT case_number, date FROM sc_decided_cases WHERE date IS NOT NULL")
            for r in cur.fetchall():
                cnum, dt = r
                d_str = str(dt)
                db_dates.add(d_str)
                if d_str not in db_cnums: db_cnums[d_str] = set()
                db_cnums[d_str].add(normalize_key(cnum))

    print("Scanning files for mismatches...")
    mismatches = [] # (filepath, date, normalized_cnum, raw_cnum)
    
    files = list(DATA_DIR.glob("*.md"))
    for f in files:
        data = parse_markdown_header(f)
        if not data: continue
        
        d = data["date"]
        c = data["cnum"]
        
        if d in db_dates:
            # Check for existing match
            found = False
            for db_c in db_cnums[d]:
                if c in db_c: # Containment check
                    found = True
                    break
            
            if not found:
                mismatches.append((f, d, c, data["raw_cnum"]))

    print(f"Found {len(mismatches)} mismatches to investigate.")
    if not mismatches: return

    # 2. Deep investigation on a sample
    sample_size = 20
    samples = mismatches[:sample_size]
    
    print(f"Investigating first {sample_size} samples by checking full_text_md in DB...")
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            for f, d, c, raw in samples:
                print(f"\nChecking: {f.name}")
                print(f"  Date: {d}")
                print(f"  Case No: {raw}")
                
                # Fetch DB records for this date
                cur.execute("SELECT id, case_number, full_text_md FROM sc_decided_cases WHERE date = %s", (d,))
                rows = cur.fetchall()
                print(f"  DB Candidates on this date: {len(rows)}")
                
                found_in_text = []
                
                for r in rows:
                    rid, r_cnum, r_text = r
                    if not r_text: continue
                    
                    # Search for case number in text (normalized)
                    norm_text = normalize_key(r_text[:1000]) # Check start of file
                    
                    if c in norm_text:
                        found_in_text.append((rid, r_cnum))
                
                if found_in_text:
                    print(f"  MATCH FOUND in full_text_md! -> IDs: {found_in_text}")
                else:
                    print(f"  No match in full_text_md either.")

if __name__ == "__main__":
    investigate()
