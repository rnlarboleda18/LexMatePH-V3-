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

def inspect_const_formats():
    conn_str = get_conn_str()
    if not conn_str:
        print("DB_CONNECTION_STRING not found in local.settings.json")
        return
        
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("--- DISTINCT ARTICLE NUMBERS (Sample 50) ---")
        cur.execute("""
            SELECT DISTINCT article_num 
            FROM const_codal 
            WHERE article_num NOT LIKE 'FC-%%' 
            ORDER BY article_num 
            LIMIT 50
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"Num: {r['article_num']}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_const_formats()
