import psycopg2
import os
import random
import json

def get_db_connection():
    with open('local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    return psycopg2.connect(conn_str)

def main():
    # 1. Read the allowed audit IDs
    with open('grok_audit_ids.txt', 'r') as f:
        audit_ids = set(f.read().strip().split(','))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 2. Find candidates from DB that are in the audit list AND have special significance
    query = """
        SELECT id FROM sc_decided_cases 
        WHERE id = ANY(%s) 
        AND significance_category IN ('MODIFICATION', 'ABANDONMENT', 'NEW DOCTRINE')
    """
    # Convert to list of INTs for Postgres
    int_ids = [int(x) for x in audit_ids if x.isdigit()]
    cur.execute(query, (int_ids,))
    candidates = [str(r[0]) for r in cur.fetchall()]
    
    # 3. Sample 5 random ones
    selected = []
    if candidates:
        selected = random.sample(candidates, min(5, len(candidates)))
    
    # 4. Always add 71574 (if it exists in audit or general, user just said "plus case ID 71574")
    # We'll just add it.
    if '71574' not in selected:
        selected.append('71574')
        
    print(f"Found {len(candidates)} candidates with special significance in the audit list.")
    print(f"Selected test IDs: {','.join(selected)}")
    
    with open('grok_special_test.txt', 'w') as f:
        f.write(','.join(selected))

    conn.close()

if __name__ == "__main__":
    main()
