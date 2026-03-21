
import os
import csv
import re
import psycopg2

csv.field_size_limit(100000000)

CLEAN_METADATA_CSV = r"analysis/sc_elib_clean_metadata.csv"
UPDATE_REPORT_CSV = r"analysis/sc_elib_update_report.csv"
MD_DIR = r"data/sc_elib_md"
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def normalize_caseno(cn):
    if not cn: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', cn).lower()

def main():
    # 1. Identify which files were "Unmatched"
    print("Loading unmatched file list...")
    unmatched_files = set()
    with open(UPDATE_REPORT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'NO_MATCH':
                unmatched_files.add(row['filename'])
    
    print(f"Found {len(unmatched_files)} unmatched files to process.")

    # 2. Get Metadata for these files (to get the Case Number to search for)
    print("Loading metadata for unmatched files...")
    file_metadata = {}
    with open(CLEAN_METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['filename'] in unmatched_files:
                file_metadata[row['filename']] = row['case_numbers']
    
    # 3. Load DB records (Targets)
    # We want records that are NOT the ones we just inserted.
    # We just inserted them with scrape_source='ELib Unmatched Upload'
    print("Loading candidate DB records...")
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    cur.execute("SELECT id, case_number FROM sc_decided_cases WHERE scrape_source != 'ELib Unmatched Upload' AND case_number IS NOT NULL")
    db_rows = cur.fetchall()
    
    # Pre-calculate normalized case numbers for DB records to speed up search
    # This might be slow if greedy, but for 60k records it's fine.
    # List of (id, norm_cn, original_cn)
    db_targets = []
    for rid, cn in db_rows:
        norm = normalize_caseno(cn)
        if norm:
            db_targets.append((rid, norm, cn))
            
    print(f"Loaded {len(db_targets)} potential target records.")
    
    merged_count = 0
    errors = 0
    
    print("Starting Merge...")
    
    for filename in unmatched_files:
        if filename not in file_metadata:
            continue
            
        case_no_str = file_metadata[filename]
        norm_search = normalize_caseno(case_no_str)
        
        if not norm_search:
            continue
            
        # Greedy Search: Is `norm_search` substring of `db_target.norm`?
        # OR is `db_target.norm` substring of `norm_search`? (Less likely for consolidation, but possible)
        # We are looking for: New File (E-02219) -> matches DB (E-02219, E-02235)
        # So `norm_search` in `target_norm`.
        
        matches = []
        for rid, t_norm, t_cn in db_targets:
            if norm_search in t_norm:
                matches.append(rid)
        
        if len(matches) == 1:
            # Found unique target!
            target_id = matches[0]
            
            # Action:
            # 1. Read content
            # 2. Update target_id
            # 3. Delete the duplicate record (where sc_url = filename)
            
            file_path = os.path.join(MD_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Update Target
                cur.execute("UPDATE sc_decided_cases SET full_text_md = %s, updated_at = NOW() WHERE id = %s", (content, target_id))
                
                # Delete Duplicate
                cur.execute("DELETE FROM sc_decided_cases WHERE sc_url = %s AND scrape_source = 'ELib Unmatched Upload'", (filename,))
                
                merged_count += 1
                if merged_count % 100 == 0:
                    conn.commit()
                    print(f"Merged {merged_count}...")
                    
            except Exception as e:
                print(f"Error merging {filename}: {e}")
                conn.rollback()
                errors += 1
        
        elif len(matches) > 1:
            # Ambiguous - skip safely
            pass
        else:
            # No match - likely truly new
            pass

    conn.commit()
    conn.close()
    
    print(f"Done. Merged & Cleaned: {merged_count}. Errors: {errors}.")

if __name__ == "__main__":
    main()
