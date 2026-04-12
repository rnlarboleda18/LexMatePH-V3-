import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        path = 'api/local.settings.json'
        if not os.path.exists(path):
            path = 'local.settings.json'
        with open(path, 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception as e:
        print(f"Error reading config: {e}")
    return None

def inspect():
    conn_str = get_conn_str()
    if not conn_str:
        return
        
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        output = []
        output.append("--- TABLES ---")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        for t in tables:
            output.append(t['table_name'])
            
        output.append("\n--- LEGAL CODES ---")
        cur.execute("SELECT code_id, short_name, full_name FROM legal_codes ORDER BY short_name")
        codes = cur.fetchall()
        for c in codes:
            output.append(f"{c['code_id']}: {c['short_name']} - {c['full_name']}")
            
        cur.close()
        conn.close()
        
        with open('api/inspect_results.txt', 'w') as f:
            f.write("\n".join(output))
        print("Done writing to api/inspect_results.txt")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
