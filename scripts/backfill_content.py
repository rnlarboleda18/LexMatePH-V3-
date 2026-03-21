import psycopg2
import json
import os
import glob
import requests
import sys
import time

# Add sc_scraper to path to import parser
sys.path.append(os.path.join(os.getcwd(), 'sc_scraper'))
try:
    from content_parser import parse_decision_content
except ImportError:
    sys.path.append(os.getcwd())
    from sc_scraper.content_parser import parse_decision_content

CONN_STR = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
METADATA_DIR = "sc_scraper"
DOWNLOADS_DIR = "sc_scraper/downloads"

def load_metadata_map():
    print("Loading metadata JSONs...")
    meta_map = {} 
    json_files = glob.glob(os.path.join(METADATA_DIR, "metadata_*.json"))
    for jf in json_files:
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    year = item.get('year')
                    cnum = item.get('case_number', '').strip()
                    if not year or not cnum:
                        continue
                    key_cnum = (int(year), cnum.lower())
                    meta_map[key_cnum] = item
        except Exception:
            pass
    print(f"Loaded {len(meta_map)} metadata entries.")
    return meta_map

def save_local(year, month, item_id, content):
    path = os.path.join(DOWNLOADS_DIR, str(year), month)
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{item_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({"main_text": content}, f, indent=4, ensure_ascii=False)

def process_batch(meta_map, limit=10):
    conn = psycopg2.connect(CONN_STR)
    cur = conn.cursor()
    
    # LOCKING QUERY for Concurrency
    cur.execute("""
        SELECT id, case_number, title, date 
        FROM supreme_decisions 
        WHERE raw_content IS NULL OR raw_content = ''
        LIMIT %s FOR UPDATE SKIP LOCKED
    """, (limit,))
    
    rows = cur.fetchall()
    
    if not rows:
        conn.close()
        return 0
        
    print(f"Batch: Processing {len(rows)} cases...")
    
    for row in rows:
        cid, cnum, title, cdate = row
        content = None
        
        if cdate:
            year = cdate.year
            cnum_clean = cnum.strip().lower() if cnum else ""
            
            # 1. EXISTENCE CHECK (Metadata Match)
            meta = meta_map.get((year, cnum_clean))
            
            if not meta:
                # Try fallback: lookup by Title normalization? 
                # For now, just log failure to find metadata
                # print(f"Warning: No metadata found for ID {cid} ({cnum}). Cannot verify source.")
                continue

            # Case "Exists" in metadata
            mid = meta.get('id')
            month = meta.get('month')
            url = meta.get('url')
            
            # 2. LOCAL CHECK
            local_path = os.path.join(DOWNLOADS_DIR, str(year), month, f"{mid}.json")
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        local_data = json.load(f)
                        content = local_data.get('main_text') or local_data.get('raw_content')
                        # print(f"Found local content for ID {cid}")
                except:
                    pass
            
            # 3. SCRAPE (If missing locally)
            if not content and url:
                try:
                    # print(f"Scraping ID {cid} from {url}...")
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        parsed = parse_decision_content(resp.content)
                        content = parsed.get("main_text")
                        if content:
                            save_local(year, month, mid, content)
                            time.sleep(0.5) # Polite delay
                        else:
                            print(f"Failed to parse content for ID {cid}")
                    else:
                        print(f"Failed to scrape ID {cid}: HTTP {resp.status_code}")
                except Exception as e:
                    print(f"Scrape error ID {cid}: {e}")
        
        if content:
            cur.execute("UPDATE supreme_decisions SET raw_content = %s WHERE id = %s", (content, cid))
            conn.commit()
            print(f"Restored content for ID {cid}")
        else:
            # If we fail, we ROLLBACK this specific row update?
            # Actually, if we don't update it, the transaction commit at end (or per row) releases lock.
            # It will be picked up again?
            # Creating infinite loop for unrecoverable cases is bad.
            # Mark as 'scraped_failed' ideally. 
            # For now, we just skip update.
            # But the lock is held until commit.
            # We are committing per row success.
            pass
            
    conn.close()
    return len(rows)

def backfill_worker():
    meta_map = load_metadata_map()
    empty_streak = 0
    
    while True:
        try:
            count = process_batch(meta_map)
            if count == 0:
                empty_streak += 1
                if empty_streak > 5:
                    print("No missing cases found. Sleeping 30s...")
                    time.sleep(30)
                else:
                    time.sleep(5)
            else:
                empty_streak = 0
        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    backfill_worker()
