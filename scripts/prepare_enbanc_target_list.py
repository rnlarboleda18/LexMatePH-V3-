import psycopg2
import json

def get_db_connection():
    with open('local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    return psycopg2.connect(conn_str)

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Selecting En Banc cases with empty separate opinions...")
    query = """
        SELECT id 
        FROM sc_decided_cases 
        WHERE (separate_opinions IS NULL OR separate_opinions::text = '[]' OR separate_opinions::text = '')
        AND full_text_md ILIKE '%En Banc%'
        AND date >= '1946-01-01'::date AND date <= '2025-12-31'::date
    """
    cur.execute(query)
    rows = cur.fetchall()
    ids = [str(r[0]) for r in rows]
    
    print(f"Found {len(ids)} target cases.")
    
    filename = 'gemini_enbanc_opinions_ids.txt'
    with open(filename, 'w') as f:
        f.write(','.join(ids))
        
    print(f"Saved IDs to {filename}")
    conn.close()

if __name__ == "__main__":
    main()
