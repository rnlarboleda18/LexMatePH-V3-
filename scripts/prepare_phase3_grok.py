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
    
    print("Searching for cases:")
    print("- AI Model: gemini-2.5-flash-lite")
    print("- Date Range: 1987-2025")
    
    query = """
        SELECT id 
        FROM sc_decided_cases 
        WHERE ai_model = 'gemini-2.5-flash-lite'
        AND date >= '1987-01-01'::date 
        AND date <= '2025-12-31'::date
        ORDER BY date DESC
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    ids = [str(r[0]) for r in rows]
    
    print(f"\nFound {len(ids)} cases matching criteria.")
    
    filename = 'grok_phase3_ids.txt'
    with open(filename, 'w') as f:
        f.write(','.join(ids))
        
    print(f"Saved IDs to {filename}")
    conn.close()

if __name__ == "__main__":
    main()
