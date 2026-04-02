
import os
import glob
import json
import psycopg2
import re

# ... (Previous imports except parse_amendment)
# Keep standard imports

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # data/LexCode/scripts
DATA_DIR = os.path.dirname(BASE_DIR)
MD_DIR = os.path.join(DATA_DIR, 'Codals', 'md')

def get_db_connection():
    # Attempt local settings first
    try:
        settings_path = os.path.join(DATA_DIR, '../../local.settings.json')
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
                return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        pass
    # Fallback to dev default
    return psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")

def parse_metadata_light(filepath):
    filename = os.path.basename(filepath)
    # Try filename fallback
    # ra_123_2000.md -> RA 123
    name_parts = filename.replace('.md', '').split('_')
    if len(name_parts) >= 2:
        prefix = name_parts[0].upper()
        number = name_parts[1]
        year = name_parts[2] if len(name_parts) > 2 else "????"
        return {
            'amendment_id': f"{prefix} {number}",
            'date': year # Approximate
        }
    return {'amendment_id': filename, 'date': 'Unknown'}

def check_status():
    print(f"--- CODEX STATUS CHECK (Regex Mode) ---")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Base RPC Code
    try:
        cur.execute("SELECT COUNT(*) FROM legal_codes WHERE full_name LIKE '%Revised Penal Code%'")
        rpc_found = cur.fetchone()[0] > 0
        if rpc_found:
             cur.execute("SELECT code_id FROM legal_codes WHERE full_name LIKE '%Revised Penal Code%' LIMIT 1")
             rpc_id = cur.fetchone()[0]
             cur.execute("SELECT COUNT(*) FROM article_versions WHERE code_id = %s", (rpc_id,))
             art_count = cur.fetchone()[0]
             print(f"[BASE] RPC Found: YES (ID: {rpc_id}) - {art_count} articles.")
        else:
             print(f"[BASE] RPC Found: NO")
    except Exception as e:
        print(f"[BASE] Error checking RPC: {e}")

    # 2. Applied Amendments
    try:
        cur.execute("SELECT DISTINCT amendment_id FROM article_versions WHERE amendment_id IS NOT NULL")
        applied_ids = {row[0] for row in cur.fetchall()}
        print(f"\n[AMENDMENTS] Applied in DB: {len(applied_ids)} unique IDs")
    except:
        applied_ids = set()
        print("\n[AMENDMENTS] Could not fetch applied amendments.")
    
    # 3. MD File Scan
    md_files = glob.glob(os.path.join(MD_DIR, "*.md"))
    md_files = [f for f in md_files if "RPC.md" not in f and "RPC_Verbatim" not in f]
    md_files.sort()
    
    print(f"\n[FILES] Found {len(md_files)} amendment files in {MD_DIR}...")
    
    pending_count = 0
    for md_file in md_files:
        try:
            meta = parse_metadata_light(md_file)
            aid = meta['amendment_id']
            # Normalize ID format if needed (e.g. RA 123 vs R.A. No. 123)
            # For now, strict check, might miss matches if format differs
            
            # Simple fuzzy check
            is_applied = False
            for applied in applied_ids:
                if aid.replace(" ",'').lower() in applied.replace(" ",'').replace('.','').lower():
                    is_applied = True
                    break
            
            if is_applied:
                status = "APPLIED"
            else:
                status = "PENDING"
                pending_count += 1
                
            print(f"  [{status:<7}] {os.path.basename(md_file):<30} (ID: {aid})")
        except Exception as e:
            print(f"  [ERROR  ] {os.path.basename(md_file)}: {e}")
            
    print(f"\nSummary: ~{pending_count} Pending Amendments (Estimated).")
    conn.close()

if __name__ == "__main__":
    check_status()
