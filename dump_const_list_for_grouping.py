import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        with open('api/local.settings.json', 'r') as f:
            config = json.load(f)
            # Make sure it's remote or local depending on what we want
            # Let's use the same logic
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception: pass
    return None

def dump_list():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, list_order, article_num, article_label, section_label, group_header, article_title, content_md
            FROM const_codal 
            WHERE book_code = 'CONST'
            ORDER BY list_order ASC 
        """)
        rows = cur.fetchall()
        
        with open('const_list_for_grouping.txt', 'w', encoding='utf-8') as f:
            f.write(f"Total rows: {len(rows)}\n")
            f.write("=" * 100 + "\n")
            for r in rows:
                content = r['content_md'] or ""
                first_line = content.split('\n')[0][:80] if content else ""
                f.write(f"Ord: {r['list_order']} | ID: {r['id']} | Num: {r['article_num']} | Lbl: {r['article_label']} | Sec: {r['section_label']} | Grp: {r['group_header']}\n")
                f.write(f"  Title: {r['article_title']}\n")
                f.write(f"  Snippet: {first_line}\n")
                f.write("-" * 100 + "\n")
                
        print("Dump complete: const_list_for_grouping.txt")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_list()
