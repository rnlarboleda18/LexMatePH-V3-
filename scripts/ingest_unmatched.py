import os
import re
import json
import psycopg
from pathlib import Path
from datetime import datetime
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
    cache = {} 
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT case_number, date FROM sc_decided_cases WHERE date IS NOT NULL")
                rows = cur.fetchall()
                for r in rows:
                    cnum, dt = r
                    date_str = str(dt)
                    norm_cnum = normalize_key(cnum)
                    if date_str not in cache: cache[date_str] = []
                    cache[date_str].append(norm_cnum)
    except Exception as e:
        print(f"Error loading DB cache: {e}")
        return None
    return cache

def parse_markdown_header(filepath):
    try:
        full_text = Path(filepath).read_text(encoding='utf-8')
        # Regex for G.R. No. and Date in header
        match = re.search(r'##\s*\[\s*(.*?),\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s*\]', full_text[:1000])
        
        if match:
            cnum_raw = match.group(1)
            date_raw = match.group(2)
            try:
                dt = datetime.strptime(date_raw, "%B %d, %Y")
                date_str = dt.strftime("%Y-%m-%d")
                
                # Logic from check_unmatched: match any alias
                cnums = []
                main_part = cnum_raw.split('(')[0]
                cnums.append(normalize_key(main_part))
                aliases = re.findall(r'\((.*?)\)', cnum_raw)
                for alias in aliases:
                    clean_alias = re.sub(r'(formerly|old no\.|aka|also known as)', '', alias, flags=re.IGNORECASE)
                    cnums.append(normalize_key(clean_alias))

                return {
                    "cnums": cnums,
                    "date": date_str,
                    "raw_cnum": cnum_raw,
                    "full_text": full_text
                }
            except:
                pass
        return None
    except:
        return None

def ingest_unmatched():
    conn_str = get_db_connection_string()
    if not conn_str: return
    
    db_cache = load_db_cache(conn_str)
    if not db_cache: return
    
    files = list(DATA_DIR.glob("*.md"))
    print(f"Scanning {len(files)} files...")
    
    to_insert = []
    
    for f in tqdm(files):
        data = parse_markdown_header(f)
        if not data: continue # Parse errors or invalid files skipped
        
        md_date = data["date"]
        md_cnums = data.get("cnums", [])
        
        is_matched = False
        if md_date in db_cache:
            candidates = db_cache[md_date]
            for db_cnum in candidates:
                for md_c in md_cnums:
                    if md_c and md_c in db_cnum:
                        is_matched = True
                        break
                if is_matched: break
        
        if not is_matched:
            # Prepare for insertion
            # We use the raw cnum for insertion as the "Case Number" label
            to_insert.append((data["raw_cnum"], md_date, data["full_text"]))
            
    print(f"Found {len(to_insert)} unmatched files to insert.")
    
    if not to_insert:
        return

    print("Inserting records...")
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Batch insert
            batch_size = 100
            for i in range(0, len(to_insert), batch_size):
                batch = to_insert[i:i+batch_size]
                cur.executemany("""
                    INSERT INTO sc_decided_cases (case_number, date, full_text_md, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                """, batch)
                conn.commit()
                print(f"Committed {min(i+batch_size, len(to_insert))} records...")

    print("Done.")

if __name__ == "__main__":
    ingest_unmatched()
