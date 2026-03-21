
import os
import psycopg
from pathlib import Path
import re

# Config
DATA_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def normalize_key(s):
    if not s: return ""
    return re.sub(r'[\W_]+', '', s).lower()

def investigate_extras():
    print("Scanning local files...")
    local_files = list(DATA_DIR.rglob("*.md"))
    local_norms = set()
    
    for f in local_files:
        # Extract case number strictly from filename
        fname = f.name
        match = re.search(r'^(.*?)_([A-Za-z]+_\d{1,2}_\d{4})', fname)
        if match:
            cnum = match.group(1)
        else:
            match_simple = re.search(r'^(.*?)_\d{4}', fname)
            if match_simple:
                 cnum = match_simple.group(1)
            else:
                 cnum = fname.replace(".md", "")
        
        local_norms.add(normalize_key(cnum))
        
    print(f"Found {len(local_files)} local files ({len(local_norms)} unique normalized keys).")

    print("\nFetching DB records...")
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, case_number, LENGTH(full_text_md), date FROM sc_decisionsv2")
            rows = cur.fetchall()
            
    print(f"Found {len(rows)} DB records.")
    
    extras = []
    for r in rows:
        rid, cnum, length, date = r
        if not cnum: continue
        
        norm = normalize_key(cnum)
        if norm not in local_norms:
            extras.append({
                "id": rid,
                "cnum": cnum,
                "length": length if length else 0,
                "date": date
            })
            
    print(f"\nFound {len(extras)} records in DB that are NOT in local files.")
    
    if extras:
        print("\nTop 20 Extra Records (by ID):")
        for e in extras[:20]:
            print(f"  ID: {e['id']} | Case: {e['cnum']} | Len: {e['length']} | Date: {e['date']}")
            
        print("\nAnalysis of Extras:")
        # Check if they are empty
        empty_count = sum(1 for e in extras if e['length'] < 100)
        print(f"  Empty/Small Content (<100 chars): {empty_count}")
        
        # Check years
        years = {}
        for e in extras:
            if e['date']:
                y = str(e['date'])[:4]
                years[y] = years.get(y, 0) + 1
        
        sorted_years = sorted(years.items(), key=lambda x: x[1], reverse=True)
        print("  Top Years:", sorted_years[:5])

if __name__ == "__main__":
    investigate_extras()
