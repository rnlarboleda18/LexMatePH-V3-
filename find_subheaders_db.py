import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        with open('api/local.settings.json', 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception: pass
    return None

def find_subheaders():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, list_order, article_num, article_label, section_label, group_header, 
                   substring(content_md from 1 for 100) as content_snippet
            FROM const_codal 
            WHERE book_code = 'CONST' AND content_md LIKE '%%###%%'
            ORDER BY list_order ASC 
        """)
        rows = cur.fetchall()
        
        print(f"Found {len(rows)} subheader rows containing '###'")
        for r in rows:
            print(f"Order: {r['list_order']} | Num: {r['article_num']} | Lbl: {r['article_label']} | Sec: {r['section_label']}")
            print(f"  Snippet: {r['content_snippet'].replace('\n', ' ')}")
            print("-" * 40)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_subheaders()
