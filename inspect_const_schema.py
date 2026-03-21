import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        with open('api/local.settings.json', 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception as e:
        print(f"Error reading config: {e}")
    return None

def inspect_const_schema():
    conn_str = get_conn_str()
    if not conn_str:
        return
        
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("--- COLUMNS IN const_codal ---")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'const_codal'
        """)
        rows = cur.fetchall()
        for r in rows:
            print(r['column_name'])
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_const_schema()
