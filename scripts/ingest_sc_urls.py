import os
import psycopg2
import csv
import re
from datetime import datetime

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
CSV_FILE = "data/sc_elib_metadata.csv"

def normalize_caseno(cn):
    if not cn or cn == "NULL": return ""
    # Remove punctuation, spaces, lowercase
    # G.R. No. 12345 -> grno12345
    return re.sub(r'[^a-zA-Z0-9]', '', cn).lower()

def parse_csv_date(date_str):
    if not date_str or date_str == "NULL": return None
    # "March 05, 1996" -> date obj
    try:
        return datetime.strptime(date_str, "%B %d, %Y").date()
    except:
        return None

def ingest_urls():
    # 1. Load CSV Data
    print("Loading CSV data...")
    csv_lookup = {} # Key: (norm_caseno, date_iso) -> url
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            parsed_date = parse_csv_date(row['date'])
            norm_cn = normalize_caseno(row['case_number'])
            url = row['url']
            
            if norm_cn and parsed_date:
                key = (norm_cn, parsed_date)
                csv_lookup[key] = url
                count += 1
                
    print(f"Loaded {count} usable records from CSV.")

    # 2. Iterate DB Record
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    try:
        print("Fetching DB records...")
        cur.execute("SELECT id, case_number, date FROM sc_decided_cases WHERE sc_url IS NULL")
        rows = cur.fetchall()
        print(f"Checking {len(rows)} DB records...")
        
        updates = []
        
        for r in rows:
            db_id = r[0]
            db_cn = r[1]
            db_date = r[2] # Actual date obj from postgres
            
            if not db_cn or not db_date:
                continue
                
            norm_db_cn = normalize_caseno(db_cn)
            
            # Lookup
            key = (norm_db_cn, db_date)
            
            if key in csv_lookup:
                url = csv_lookup[key]
                updates.append((url, db_id))
        
        if updates:
            print(f"Found {len(updates)} matches. Updating DB...")
            
            # Batch update
            batch_size = 1000
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i+batch_size]
                cur.executemany("UPDATE sc_decided_cases SET sc_url = %s WHERE id = %s", batch)
                conn.commit()
                print(f"Committed batch {i//batch_size + 1}")
                
            print("Bulk update complete.")
        else:
            print("No matches found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_urls()
