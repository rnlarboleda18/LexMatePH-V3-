import os
import re
import json
import psycopg
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

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

def load_db_cache(conn_str):
    print("Loading DB Cache...")
    cache = {} # { 'YYYY-MM-DD': [ (id, normalized_cnum), ... ] }
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, case_number, date FROM sc_decided_cases WHERE date IS NOT NULL")
                rows = cur.fetchall()
                for r in rows:
                    rid, cnum, dt = r
                    date_str = str(dt) # '2018-05-11'
                    norm_cnum = normalize_key(cnum)
                    
                    if date_str not in cache:
                        cache[date_str] = []
                    cache[date_str].append((rid, norm_cnum))
    except Exception as e:
        print(f"Error loading DB cache: {e}")
        return None
    
    print(f"Loaded {sum(len(v) for v in cache.values())} records into cache.")
    return cache

def parse_markdown_header(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Read first 20 lines for header info
            lines = [f.readline() for _ in range(20)]
            content_start = f.tell()
            # Read rest of content? No, need full content for update
            # But let's verify header first before reading 50kb+ file
            
        full_text = Path(filepath).read_text(encoding='utf-8')
        
        # Regex for G.R. No. and Date in header
        # ## [ G.R. No. 237428, May 11, 2018 ]
        # Updated to be more permissive for A.M., A.C., P.E.T., etc.
        header_match = re.search(r'##\s*\[\s*(.*?),\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s*\]', full_text[:1000])
        
        if header_match:
            cnum_raw = header_match.group(1)
            date_raw = header_match.group(2)
            
            try:
                dt = datetime.strptime(date_raw, "%B %d, %Y")
                date_str = dt.strftime("%Y-%m-%d")
                
                # Logic: Extract aliases. 
                # e.g. "G.R. No. 123 (Formerly G.R. No. 456)" -> ["grno123", "grno456"]
                cnums = []
                
                # 1. Main part (before first paren)
                main_part = cnum_raw.split('(')[0]
                cnums.append(normalize_key(main_part))
                
                # 2. Alias parts (inside parens)
                aliases = re.findall(r'\((.*?)\)', cnum_raw)
                for alias in aliases:
                    # Filter out purely non-cnum text like "Formerly" if possible? 
                    # normalize_key removes spaces/special chars, so "Formerly G.R. 123" -> "formerlygr123"
                    # But if DB has "G.R. 123", "formerlygr123" won't match "gr123".
                    # DB might likely have just "gr123".
                    # Let's try to be smart: if alias contains "Formerly" or "Also known as", remove that phrase?
                    # Or just rely on containment: "gr123" is in "formerlygr123"? NO, containment is valid if MD is substring of DB.
                    # DB: "gr123"
                    # MD: "formerlygr123"
                    # "formerlygr123" in "gr123" -> False.
                    # "gr123" in "formerlygr123" -> True. But we check `if md_cnum in db_cnum`.
                    # So if MD is "formerlygr123" and DB is "gr123", it fails (md too long).
                    # We need to strip "Formerly", "Old No.", etc.
                    
                    clean_alias = re.sub(r'(formerly|old no\.|aka|also known as)', '', alias, flags=re.IGNORECASE)
                    cnums.append(normalize_key(clean_alias))
                
                return {
                    "cnums": cnums,
                    "date": date_str,
                    "content": full_text
                }
            except:
                pass
                
        # Fallback: Try finding date in other format or strict G.R. No parsing
        # Some files might have different header structure
        
        return None
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

def process_file(filepath, db_cache):
    data = parse_markdown_header(filepath)
    if not data:
        return None
    
    md_date = data["date"]
    # We now expect data["cnums"] to always be present
    md_cnums = data.get("cnums", [])
    if not md_cnums and "cnum" in data:
         md_cnums = [data["cnum"]]
    
    if md_date not in db_cache:
        return None
    
    candidates = db_cache[md_date]
    matches = []
    
    for rid, db_cnum in candidates:
        # Check if ANY of the MD cnums are in the DB cnum
        for md_c in md_cnums:
            if md_c and md_c in db_cnum:
                matches.append(rid)
                break 
    
    if matches:
        # If multiple matches (unlikely with date + cnum), just take first or log?
        # User said "consolidated cases... match... even if md file has only one"
        # Since we are overwriting full_text_md, if one MD file matches multiple DB entries 
        # (e.g. duplicate entries for same case?), allow update for all.
        return (matches, data["content"])
    
    return None

def ingest():
    conn_str = get_db_connection_string()
    if not conn_str: return
    
    db_cache = load_db_cache(conn_str)
    if not db_cache: return
    
    files = list(DATA_DIR.glob("*.md"))
    print(f"Scanning {len(files)} files...")
    
    updates = [] # List of (id, content)
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_file = {executor.submit(process_file, f, db_cache): f for f in files}
        
        for future in tqdm(as_completed(future_to_file), total=len(files)):
            result = future.result()
            if result:
                ids, content = result
                for rid in ids:
                    updates.append((rid, content))
    
    print(f"Ready to update {len(updates)} records.")
    
    # Batch updates
    BATCH_SIZE = 100
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(updates), BATCH_SIZE):
                batch = updates[i:i+BATCH_SIZE]
                
                # Use execute_batch or just simple executemany
                # Since we are updating text, it might be heavy.
                # Let's use a temporary table for bulk update if possible, or just individual updates in transaction
                
                # Simple loop for safety/simplicity first
                for rid, content in batch:
                    cur.execute("UPDATE sc_decided_cases SET full_text_md = %s, updated_at = NOW() WHERE id = %s", (content, rid))
                
                conn.commit()
                if i % 1000 == 0:
                    print(f"Committed {i} updates...")
                    
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest()
