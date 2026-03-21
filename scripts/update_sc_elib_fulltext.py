
import os
import csv
import re
import psycopg2
from datetime import datetime

# Configuration
CSV_PATH = r"analysis/sc_elib_clean_metadata.csv"
MD_DIR = r"data/sc_elib_md"
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
REPORT_CSV = r"analysis/sc_elib_update_report.csv"

def normalize_caseno(cn):
    if not cn: return ""
    # Remove "G.R. No.", "No.", whitespace, punctuation
    return re.sub(r'[^a-zA-Z0-9]', '', cn).lower()

def to_date_obj(d_str):
    if not d_str or d_str == 'NOT_FOUND': return None
    # Expecting "Month Day, Year" e.g., "January 27, 2006"
    try:
        return datetime.strptime(d_str.strip(), "%B %d, %Y").date()
    except:
        try:
             # Fallback for some variations? E.g. "Jan. 27, 2006"
             return datetime.strptime(d_str.strip().replace('.', ''), "%b %d, %Y").date()
        except:
            return None

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    print("Loading CSV metadata...")
    csv_data = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_data.append(row)
    print(f"Loaded {len(csv_data)} CSV records.")

    print("Fetching DB records...")
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    # Fetch id, case_number, date
    cur.execute("SELECT id, case_number, date FROM sc_decided_cases WHERE case_number IS NOT NULL")
    db_rows = cur.fetchall()
    
    # Build lookup map: (normalized_case_number, date) -> id
    # Also just (normalized_case_number) -> list of (id, date) for fuzzy date matching
    db_lookup_exact = {}
    db_lookup_cn = {}
    
    for row_id, cn, dt in db_rows:
        norm_cn = normalize_caseno(cn)
        if not norm_cn: continue
        
        # Exact Map
        key_exact = (norm_cn, dt)
        if key_exact not in db_lookup_exact:
            db_lookup_exact[key_exact] = []
        db_lookup_exact[key_exact].append(row_id)
        
        # CN Map
        if norm_cn not in db_lookup_cn:
            db_lookup_cn[norm_cn] = []
        db_lookup_cn[norm_cn].append({'id': row_id, 'date': dt})

    print(f"Built lookup for {len(db_rows)} DB records.")

    updates_count = 0
    matches_found = 0
    multi_matches = 0
    no_matches = 0
    
    report_rows = []

    print("Processing matches...")
    
    # We will buffer updates
    # But for 26k, maybe individual updates are slow. Let's try batching or just simple loop first.
    # Simple loop with periodic commit is safer for debugging.
    
    for row in csv_data:
        csv_cn = row['case_numbers']
        csv_date_str = row['date']
        filename = row['filename']
        
        norm_cn = normalize_caseno(csv_cn)
        csv_date = to_date_obj(csv_date_str)
        
        match_id = None
        match_type = "NONE"
        
        # 1. Try Exact Match (CN + Date)
        if csv_date:
            key = (norm_cn, csv_date)
            if key in db_lookup_exact:
                ids = db_lookup_exact[key]
                if len(ids) == 1:
                    match_id = ids[0]
                    match_type = "EXACT"
                else:
                    match_type = "MULTI_EXACT"
        
        # 2. If no exact match, try CN match
        if not match_id:
             if norm_cn in db_lookup_cn:
                 candidates = db_lookup_cn[norm_cn]
                 if len(candidates) == 1:
                     # Single candidate found matching CN.
                     # If CSV Date is missing, or matches DB date, or we are feeling lucky?
                     # Since we trust the Case Number primary matching, let's accept single matches.
                     # Even if date implies update (e.g. resolution vs decision), the content *likely* belongs there if unique.
                     match_id = candidates[0]['id']
                     match_type = "CN_ONLY_SINGLE"
                 else:
                     match_type = "CN_MULTI"
        
        # Content Reading
        file_path = os.path.join(MD_DIR, filename)
        if not os.path.exists(file_path):
             report_rows.append({'filename': filename, 'status': "FILE_MISSING", 'match_type': match_type, 'db_id': ''})
             continue
             
        if match_id:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Update DB
                cur.execute("UPDATE sc_decided_cases SET full_text_md = %s, updated_at = NOW() WHERE id = %s", (content, match_id))
                matches_found += 1
                updates_count += 1
                report_rows.append({'filename': filename, 'status': "UPDATED", 'match_type': match_type, 'db_id': match_id})
                
                if updates_count % 100 == 0:
                    conn.commit()
                    print(f"Updated {updates_count}...")
                    
            except Exception as e:
                report_rows.append({'filename': filename, 'status': f"ERROR: {e}", 'match_type': match_type, 'db_id': match_id})
                conn.rollback()
        else:
             no_matches += 1
             report_rows.append({'filename': filename, 'status': "NO_MATCH", 'match_type': match_type, 'db_id': ''})

    conn.commit()
    conn.close()
    
    print(f"Finished. Updated: {updates_count}, No Match: {no_matches}.")
    
    # Write Report
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ['filename', 'status', 'match_type', 'db_id']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)
    print(f"Report saved to {REPORT_CSV}")

if __name__ == "__main__":
    main()
