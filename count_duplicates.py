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

def count_duplicates():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT id, article_num, list_order, content_md FROM const_codal WHERE article_num = 'II-0'")
        rows = cur.fetchall()
        print(f"--- FOUND {len(rows)} ROWS FOR II-0 ---")
        for r in rows:
             print(f"ID: {r['id']} | Order: {r['list_order']}")
             print(f"Content: {repr(r['content_md'][:100])}")
             print("-" * 40)
             
        cur.close()
        conn.close()
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    count_duplicates()
