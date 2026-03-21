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

def inspect_article_ii():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, list_order, article_num, section_label, content_md 
            FROM const_codal 
            WHERE book_code = 'CONST' AND article_label = 'ARTICLE II'
            ORDER BY list_order ASC 
        """)
        rows = cur.fetchall()
        
        print(f"Found {len(rows)} rows for Article II")
        for r in rows:
            content = r['content_md'] or ""
            # Print row info and first 100 chars of content
            print(f"Ord: {r['list_order']} | Num: {r['article_num']} | Sec: {r['section_label']}")
            print(f"  Content: {content.replace('\n', ' ')[:100]}")
            print("-" * 40)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_article_ii()
