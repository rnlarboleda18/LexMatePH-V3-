
import os
import csv
import re
import psycopg2
from collections import defaultdict

csv.field_size_limit(100000000)

CLEAN_METADATA_CSV = r"analysis/sc_elib_clean_metadata.csv"
UPDATE_REPORT_CSV = r"analysis/sc_elib_update_report.csv"
MD_DIR = r"data/sc_elib_md"
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def normalize_caseno(cn):
    if not cn: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', cn).lower()

def extract_numbers(s):
    # Returns a set of numeric strings found in the normalized string
    # e.g. "grno12345" -> {"12345"}
    return set(re.findall(r'\d+', s))

def main():
    print("Loading unmatched file list...")
    unmatched_files = set()
    with open(UPDATE_REPORT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # We must re-process all NO_MATCH, but check if they still exist first
            if row['status'] == 'NO_MATCH':
                unmatched_files.add(row['filename'])

    print(f"Found {len(unmatched_files)} unmatched files to potentially merge.")
    
    file_metadata = {}
    with open(CLEAN_METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['filename'] in unmatched_files:
                file_metadata[row['filename']] = row['case_numbers']

    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    # Verify which unmatched uploads still exist (some were merged by previous run)
    print("Verifying remaining duplicates...")
    cur.execute("SELECT sc_url FROM sc_decided_cases WHERE scrape_source = 'ELib Unmatched Upload'")
    existing_dupes = set(row[0] for row in cur.fetchall())
    
    # Filter our work list
    files_to_process = [f for f in unmatched_files if f in existing_dupes and f in file_metadata]
    print(f"Actually processing {len(files_to_process)} records (others already merged or missing).")

    print("Loading candidate DB records...")
    cur.execute("SELECT id, case_number FROM sc_decided_cases WHERE scrape_source != 'ELib Unmatched Upload' AND case_number IS NOT NULL")
    db_rows = cur.fetchall()

    # Build Index
    # Map: number_string -> list of (id, norm_cn)
    print("Building numeric index...")
    index = defaultdict(list)
    targets_map = {} # id -> (norm, cn)
    
    for rid, cn in db_rows:
        norm = normalize_caseno(cn)
        if not norm: continue
        
        targets_map[rid] = norm
        nums = extract_numbers(norm)
        for n in nums:
            # Only index significant numbers (len > 2 to avoid noise like '1', '2')
            if len(n) > 2:
                index[n].append(rid)
    
    print(f"Index built. Keys: {len(index)}")
    
    merged_count = 0
    errors = 0
    
    print("Starting Merge...")
    for filename in files_to_process:
        case_no_str = file_metadata[filename]
        norm_search = normalize_caseno(case_no_str)
        if not norm_search: continue
        
        nums = extract_numbers(norm_search)
        candidate_ids = set()
        
        # Gather candidates that share at least one significant number
        for n in nums:
            if len(n) > 2 and n in index:
                candidate_ids.update(index[n])
        
        if not candidate_ids:
            continue
            
        # Refine Match
        matches = []
        for rid in candidate_ids:
            t_norm = targets_map[rid]
            # Check substring
            if norm_search in t_norm:
                matches.append(rid)
        
        if len(matches) == 1:
            target_id = matches[0]
            
            file_path = os.path.join(MD_DIR, filename)
            try:
                # Need to read file again?
                # Actually, we can just MOVE the content from the duplicate record to the target?
                # But we have the file locally, safer to read file.
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                cur.execute("UPDATE sc_decided_cases SET full_text_md = %s, updated_at = NOW() WHERE id = %s", (content, target_id))
                cur.execute("DELETE FROM sc_decided_cases WHERE sc_url = %s AND scrape_source = 'ELib Unmatched Upload'", (filename,))
                
                merged_count += 1
                if merged_count % 100 == 0:
                    conn.commit()
                    print(f"Merged {merged_count}...")
                    
            except Exception as e:
                print(f"Error {filename}: {e}")
                conn.rollback()
                errors += 1
                
    conn.commit()
    conn.close()
    
    print(f"Done. Merged: {merged_count}. Errors: {errors}")

if __name__ == "__main__":
    main()
