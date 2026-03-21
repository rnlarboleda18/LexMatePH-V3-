import sqlite3
import psycopg2
import json
import re
import os
from datetime import datetime

def get_pg_connection():
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
        return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        return psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")

def normalize_case_number(cn):
    if not cn: return ""
    # Remove "G.R. No.", spaces, dots, and make lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', cn).lower()

def parse_sqlite_case(case_title_field):
    # Example: "Agabon v. NLRC\n\n(G.R. No. 158693, Nov 17, 2004)"
    gr_match = re.search(r'G\.R\. No\. ([^,)]+)', case_title_field)
    date_match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', case_title_field)
    
    gr = gr_match.group(1).strip() if gr_match else None
    dt_str = date_match.group(1).strip() if date_match else None
    
    dt = None
    if dt_str:
        try:
            dt = datetime.strptime(dt_str, '%b %d, %Y').date()
        except:
            try:
                dt = datetime.strptime(dt_str, '%B %d, %Y').date()
            except:
                pass
                
    return gr, dt

def run_matching():
    # SQLite
    sl_conn = sqlite3.connect('api/questions.db')
    sl_cur = sl_conn.cursor()
    sl_cur.execute('SELECT "Case Title" FROM doctrinal_cases')
    sl_rows = sl_cur.fetchall()
    
    # PG
    pg_conn = get_pg_connection()
    pg_cur = pg_conn.cursor()
    
    matches = []
    misses = []
    
    for row in sl_rows:
        raw_title = row[0]
        gr, dt = parse_sqlite_case(raw_title)
        
        if not gr or not dt:
            misses.append({"raw": raw_title, "reason": "Could not parse GR or Date"})
            continue
            
        norm_gr = normalize_case_number(gr)
        
        # Search PG by Date + Case Number
        # We search if the normalized component exists in the comma-separated case_number field
        pg_cur.execute("""
            SELECT id, case_number, date, short_title 
            FROM sc_decided_cases 
            WHERE date = %s
        """, (dt,))
        
        potentials = pg_cur.fetchall()
        matched_row = None
        for pid, pcn, pdt, pst in potentials:
            if not pcn: continue # Skip if PG case number is NULL
            
            # Check if any part of PG case_number matches
            pg_cns = re.split(r'[,&/]', pcn)
            if any(norm_gr in normalize_case_number(c) for c in pg_cns) or (norm_gr in normalize_case_number(pcn)):
                matched_row = (pid, pcn, pdt, pst)
                break
        
        if matched_row:
            matches.append({
                "sqlite_gr": gr,
                "sqlite_date": str(dt),
                "pg_id": matched_row[0],
                "pg_case": matched_row[1],
                "pg_title": matched_row[3]
            })
        else:
            # Try searching just by GR Number if Date failed or returned no matches
            if gr:
                pg_cur.execute("SELECT id, case_number, date, short_title FROM sc_decided_cases WHERE case_number ILIKE %s", (f'%{gr}%',))
                retry = pg_cur.fetchone()
                if retry:
                    matches.append({
                        "sqlite_gr": gr,
                        "sqlite_date": str(dt),
                        "pg_id": retry[0],
                        "pg_case": retry[1],
                        "pg_title": retry[3],
                        "note": "Matched by GR only (Date mismatch or missing)"
                    })
                else:
                    misses.append({"gr": gr, "date": str(dt), "raw": raw_title})
            else:
                misses.append({"raw": raw_title, "reason": "No GR parsed from SQLite"})

    sl_conn.close()
    pg_conn.close()
    
    return matches, misses

if __name__ == "__main__":
    matches, misses = run_matching()
    print(f"Total Doctrinal: {len(matches) + len(misses)}")
    print(f"Matched: {len(matches)}")
    print(f"Missed: {len(misses)}")
    
    # Save detailed report
    with open('doctrinal_match_report.json', 'w') as f:
        json.dump({"matches": matches, "misses": misses}, f, indent=2)
    
    print("\nReport saved to doctrinal_match_report.json")
