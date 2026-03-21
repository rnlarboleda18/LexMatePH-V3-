import os
import re
import psycopg2
from datetime import datetime

# DB Connection
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
MD_DIR = "data/sc_elib_md (missing from lawphil)"

def normalize_caseno(cn):
    if not cn: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', cn).lower()

def get_db_records():
    print("Fetching DB records for de-duplication...")
    records = set()
    db_by_date = {} 
    
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    cur.execute("SELECT case_number, date FROM sc_decided_cases WHERE case_number IS NOT NULL AND date IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    
    for cn, d in rows:
        norm_cn = normalize_caseno(cn)
        if norm_cn and d:
            records.add((norm_cn, d))
            if d not in db_by_date: db_by_date[d] = set()
            db_by_date[d].add(norm_cn)
            
    print(f"Loaded {len(records)} DB records for duplication check.")
    return records, db_by_date

def is_duplicate(norm_cn, d, db_set, db_by_date):
    if (norm_cn, d) in db_set: return True
    if d in db_by_date:
        for db_cn in db_by_date[d]:
            if db_cn in norm_cn or norm_cn in db_cn: return True
    return False

def extract_metadata_for_dedupe(content):
    meta = {'case_number': None, 'date': None}
    lines = content.split('\n')
    header_regex = re.compile(r'\[\s*(.*?),\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})\s*\]', re.IGNORECASE)
    for line in lines[:20]:
         match = header_regex.search(line)
         if match:
             meta['case_number'] = match.group(1).strip()
             try:
                 meta['date'] = datetime.strptime(match.group(2).strip(), "%B %d, %Y").date()
             except: pass
             break
    return meta

def ingest_files():
    db_set, db_by_date = get_db_records()
    files = [f for f in os.listdir(MD_DIR) if f.endswith(".md")]
    print(f"Scanning {len(files)} files...")
    
    to_insert = []
    
    for filename in files:
        path = os.path.join(MD_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Deduplication
        meta = extract_metadata_for_dedupe(content)
        if meta['case_number'] and meta['date']:
            norm_cn = normalize_caseno(meta['case_number'])
            if is_duplicate(norm_cn, meta['date'], db_set, db_by_date):
                continue
        
        to_insert.append({'filename': filename, 'content': content})
        
    print(f"Found {len(to_insert)} UNIQUE files to ingest.")
    
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    success_count = 0
    
    for item in to_insert:
        try:
            elib_id = item['filename'].replace('.md', '')
            sc_url = f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{elib_id}"
            
            # Simple INSERT without ON CONFLICT
            cur.execute("""
                INSERT INTO sc_decided_cases 
                (full_text_md, scrape_source, sc_url, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (item['content'], 'E-Library Scraper', sc_url))
            
            if cur.fetchone():
                success_count += 1
                
        except Exception as e:
            print(f"Failed to insert {item['filename']}: {e}")
            conn.rollback()
            continue
            
        conn.commit()
    
    conn.close()
    print(f"Successfully ingested {success_count} new cases (Full Text + URL Only).")

if __name__ == "__main__":
    ingest_files()
