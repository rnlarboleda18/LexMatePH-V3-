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

def print_full_ii0():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT content_md FROM const_codal WHERE article_num = 'II-0'")
        row = cur.fetchone()
        if row:
             print("--- FULL CONTENT FOR II-0 ---")
             print(repr(row['content_md'])) # Use repr to see exact characters
        cur.close()
        conn.close()
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    print_full_ii0()
