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
         pass
    return None

def compare_rows():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("--- CONTENT FOR II-0 ---")
        cur.execute("SELECT content_md FROM const_codal WHERE article_num = 'II-0'")
        row_ii0 = cur.fetchone()
        if row_ii0:
             print(row_ii0['content_md'])
             
        print("\n--- CONTENT FOR II-1 ---")
        cur.execute("SELECT content_md FROM const_codal WHERE article_num = 'II-1'")
        row_ii1 = cur.fetchone()
        if row_ii1:
             print(row_ii1['content_md'])
             
        cur.close()
        conn.close()
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    compare_rows()
