import re
import psycopg2
import os

INPUT_FILE = r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\doctrinal_cases_full_list.txt'
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def normalize_gr(gr):
    if not gr: return ""
    clean = gr.upper().replace(".", "").replace(" ", "")
    clean = clean.replace("GRNO", "").replace("GR", "")
    clean = clean.replace("ACNO", "").replace("AC", "")
    clean = clean.replace("AMNO", "").replace("AM", "")
    clean = clean.replace("BMNO", "").replace("BM", "")
    return clean.strip()

def extract_case_numbers(text):
    if not text: return []
    pattern = r'(?:G\.R\.|A\.C\.|A\.M\.|B\.M\.|UDK)[.\s]*No\.?\s*([L\d\-]+)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    pattern2 = r'(?:G\.R\.|A\.C\.|A\.M\.|B\.M\.|UDK)\s+([L\d\-]+)'
    matches2 = re.findall(pattern2, text, re.IGNORECASE)
    return list(set(matches + matches2))

def mark_doctrinal_deep():
    print(f"Reading target list from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    target_numbers = extract_case_numbers(content)
    normalized_targets = set(normalize_gr(c) for c in target_numbers)
    print(f"Targets: {len(normalized_targets)} unique IDs found in file.")

    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # 1. First, match against existing case_number (Fast Pass)
    print("Pass 1: Checking extracted metadata...")
    cur.execute("SELECT id, case_number FROM sc_decided_cases WHERE case_number IS NOT NULL")
    rows = cur.fetchall()
    
    ids_to_mark = set()
    
    for rid, case_no in rows:
        parts = re.split(r'[;,]', case_no)
        for p in parts:
            if normalize_gr(p) in normalized_targets:
                ids_to_mark.add(rid)
                break
                
    print(f"Pass 1 matched {len(ids_to_mark)} cases.")

    # 2. MATCH AGAINST NULL case_number using text snippet (Deep Pass)
    print("Pass 2: Scanning raw text of unindexed cases...")
    cur.execute("SELECT id, left(full_text_md, 500) FROM sc_decided_cases WHERE case_number IS NULL OR case_number = ''")
    # Fetch in chunks if needed, but 64k items is fine for memory (~30MB)
    rows = cur.fetchall()
    
    for rid, text_snippet in rows:
        extracted = extract_case_numbers(text_snippet)
        for ex in extracted:
            if normalize_gr(ex) in normalized_targets:
                ids_to_mark.add(rid)
                break
    
    print(f"Total matched IDs after Pass 2: {len(ids_to_mark)}")
    
    if ids_to_mark:
        print(f"Marking {len(ids_to_mark)} cases as doctrinal...")
        chunk_size = 1000
        id_list = list(ids_to_mark)
        
        for i in range(0, len(id_list), chunk_size):
            chunk = tuple(id_list[i:i+chunk_size])
            cur.execute(f"UPDATE sc_decided_cases SET is_doctrinal = TRUE WHERE id IN %s", (chunk,))
            conn.commit()
            print(f"Updated chunk {i}-{i+len(chunk)}")
            
        print("Done.")
    else:
        print("No matches found.")

    conn.close()

if __name__ == "__main__":
    mark_doctrinal_deep()
