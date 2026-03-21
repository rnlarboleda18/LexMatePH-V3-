import psycopg2
import json

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def extract_non_gr_ids():
    try:
        with open('target_redigest_ids.txt', 'r') as f:
            content = f.read().replace('\n', ',')
            target_ids = [int(x.strip()) for x in content.split(',') if x.strip().isdigit()]
    except FileNotFoundError:
        print("Error: target_redigest_ids.txt not found.")
        return

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM sc_decided_cases 
        WHERE id = ANY(%s) 
          AND ai_model = 'gemini-2.5-flash-lite'
          AND case_number NOT ILIKE 'G.R.%%'
          AND case_number NOT ILIKE 'GR %%'
    """, (target_ids,))
    
    rows = cur.fetchall()
    ids = [str(r[0]) for r in rows]
    
    with open('target_non_gr_ids.txt', 'w') as f:
        f.write(",".join(ids))
        
    print(f"Extracted {len(ids)} non-GR IDs to target_non_gr_ids.txt")
    
    # Print first 5 for user report
    print("First 5 IDs:", ids[:5])
    
    conn.close()

if __name__ == "__main__":
    extract_non_gr_ids()
