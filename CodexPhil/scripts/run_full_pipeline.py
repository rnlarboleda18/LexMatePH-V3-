
import os
import subprocess
import sys
import glob
import json
import psycopg2
from parse_amendment import parse_amendment_document

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # data/CodexPhil
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
MD_DIR = os.path.join(BASE_DIR, 'Codals', 'md')

def get_db_connection():
    try:
        settings_path = os.path.join(BASE_DIR, '../../local.settings.json') # Adjust relative path
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
                return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        pass
    return psycopg2.connect("postgres://postgres:b66398241bfe483ba5b20ca5356a87be@127.0.0.1:5432/lexmateph-ea-db")

def get_applied_amendments():
    """Fetch all amendment IDs that exist in the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT amendment_id FROM article_versions WHERE amendment_id IS NOT NULL")
        return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()

def run_pipeline():
    print(f"\n{'='*70}")
    print("CODEX AUTOMATED PIPELINE")
    print(f"{'='*70}\n")
    
    # Step 1: Convert HTML to MD
    print("[1/3] Running HTML to Markdown Converter...")
    converter_script = os.path.join(BASE_DIR, 'codex_html_convert_to_md.py')
    result = subprocess.run([sys.executable, converter_script], cwd=BASE_DIR, capture_output=False)
    if result.returncode != 0:
        print("Error in conversion step.")
        sys.exit(1)
        
    # Step 2: Scan for Amendments
    print("\n[2/3] Scanning for pending amendments...")
    md_files = glob.glob(os.path.join(MD_DIR, "*.md"))
    
    # Filter out base files (RPC.md)
    md_files = [f for f in md_files if "RPC.md" not in f]
    
    # Sort chronologically by filename (assuming naming convention like ra_123_1990.md) or just name
    md_files.sort()
    
    applied_ids = get_applied_amendments()
    print(f"Index: Found {len(applied_ids)} already applied amendments in DB.")
    
    to_process = []
    
    for md_file in md_files:
        try:
            # Quick parse to get ID
            meta = parse_amendment_document(md_file)
            aid = meta['amendment_id']
            
            if aid in applied_ids:
                print(f"  [SKIP] {os.path.basename(md_file)} ({aid}) - Already applied")
            else:
                formatted_date = meta['date'] if meta['date'] else "Unknown Date"
                print(f"  [Px] {os.path.basename(md_file)} ({aid}) - Date: {formatted_date}")
                to_process.append((md_file, meta['date']))
        except Exception as e:
            print(f"  [ERROR] Could not parse {os.path.basename(md_file)}: {e}")

    # Sort pending by date to ensure chronological application
    # Simple sort; assuming YYYY-MM-DD string sort works roughly well, but real date obj is better
    to_process.sort(key=lambda x: x[1] if x[1] else "9999-99-99")
    
    if not to_process:
        print("\nAll amendments are up to date! Nothing to do.")
        return

    # Step 3: Execute Successively
    print(f"\n[3/3] Processing {len(to_process)} new amendments successively...")
    
    processor_script = os.path.join(SCRIPTS_DIR, 'process_amendment.py')
    
    failed_files = []
    
    for md_file, date in to_process:
        print(f"\n>>> Processing: {os.path.basename(md_file)}")
        proc_result = subprocess.run([sys.executable, processor_script, "--file", md_file], cwd=BASE_DIR)
        
        if proc_result.returncode != 0:
            print(f"\n!!! WARNING: Issues processing {os.path.basename(md_file)}. Continuing pipeline...")
            failed_files.append(os.path.basename(md_file))
            
    print(f"\n{'='*70}")
    print("PIPELINE COMPLETE")
    if failed_files:
        print(f"Completed with {len(failed_files)} warnings/partial failures:")
        for f in failed_files:
            print(f" - {f}")
    else:
        print("All amendments processed successfully.")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run_pipeline()
