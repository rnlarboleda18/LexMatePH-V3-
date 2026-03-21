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

def dump_duplicates():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get duplicate groups
        cur.execute("""
            SELECT article_label, section_label, COUNT(*) as count 
            FROM const_codal 
            WHERE book_code = 'CONST'
            GROUP BY article_label, section_label 
            HAVING COUNT(*) > 1
        """)
        dups = cur.fetchall()
        
        print(f"Found {len(dups)} duplicate pairs")
        
        for d in dups:
            article_label = d['article_label']
            section_label = d['section_label']
            print(f"\n=== DUPLICATES FOR {article_label} | {section_label} ({d['count']} rows) ===")
            
            # Fetch the actual rows
            cur.execute("""
                SELECT id, list_order, article_num, article_title, section_label, group_header, substring(content_md from 1 for 100) as content_snippet
                FROM const_codal 
                WHERE book_code = 'CONST' AND article_label = %s AND section_label = %s
                ORDER BY list_order
            """, (article_label, section_label))
            
            rows = cur.fetchall()
            for r in rows:
                print(f"  Order: {r['list_order']} | ID: {r['id']} | Num: {r['article_num']}")
                print(f"    Title: {r['article_title']}")
                print(f"    Group: {r['group_header']}")
                print(f"    Snippet: {r['content_snippet'].replace('\n', ' ')}")
                print("-" * 20)
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_duplicates()
