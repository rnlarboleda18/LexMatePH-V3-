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

def dump_const_structure():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, article_num, article_label, section_label, article_title, list_order, 
                   substring(content_md from 1 for 100) as content_snippet
            FROM const_codal 
            ORDER BY list_order ASC 
            LIMIT 50
        """)
        rows = cur.fetchall()
        print(f"--- DUMPING FIRST 50 ROWS OF const_codal ---")
        for r in rows:
             print(f"Order: {r['list_order']} | Num: {r['article_num']} | Label: {r['article_label']} | Section: {r['section_label']} | Title: {r['article_title']}")
             print(f"  Snippet: {r['content_snippet'].replace('\n', ' ')}")
             print("-" * 40)
             
        cur.close()
        conn.close()
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    dump_const_structure()
