
import psycopg
import os
import json

CONN_STR = json.load(open('api/local.settings.json'))['Values']['DB_CONNECTION_STRING']
md_path = 'data/sc_elib_md/64003.md'
md_content = open(md_path, encoding='utf-8').read()

print(f"Reading {md_path}, length: {len(md_content)}")

with psycopg.connect(CONN_STR) as conn:
    with conn.cursor() as cur:
        # Check first
        print("Searching for G.R. No. 237428, 2018-05-11...")
        cur.execute("SELECT id, case_number FROM sc_decided_cases WHERE case_number = 'G.R. No. 237428' AND date = '2018-05-11'")
        res = cur.fetchone()
        
        target_id = None
        
        if res:
             print(f"Found record: ID={res[0]}, CNum={res[1]}")
             target_id = res[0]
        else:
             print("Record not found matching exact case number/date.")
             # Try date only
             cur.execute("SELECT id, case_number FROM sc_decided_cases WHERE date = '2018-05-11'")
             rows = cur.fetchall()
             print(f"Found {len(rows)} cases on 2018-05-11: {[r[1] for r in rows]}")
             # logic to find 237428 in candidates
             for r in rows:
                 if "237428" in r[1]:
                     target_id = r[0]
                     print(f"Fuzzy match: {r[1]} -> ID {target_id}")
                     break
        
        if target_id:
             cur.execute("UPDATE sc_decided_cases SET full_text_md = %s, updated_at = NOW() WHERE id = %s", (md_content, target_id))
             print(f"Updated record {target_id} successfully.")
        else:
             print("Could not find target record to update.")
