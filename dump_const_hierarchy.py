import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn_str():
    # Try reading from api/local.settings.json first (Remote)
    try:
        with open('api/local.settings.json', 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception:
        pass
    # Fallback to local
    try:
        with open('local.settings.json', 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception:
         pass
    return None

def dump_hierarchy():
    conn_str = get_conn_str()
    if not conn_str:
        print("No connection string found")
        return
        
    print(f"Connecting to: {conn_str.split('@')[-1] if '@' in conn_str else '...'}")
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, list_order, group_header, article_num, article_label, article_title, section_label, structural_map
            FROM const_codal 
            ORDER BY list_order ASC 
        """)
        rows = cur.fetchall()
        
        with open('const_hierarchy_dump.txt', 'w', encoding='utf-8') as f:
            f.write(f"Total rows: {len(rows)}\n")
            f.write("=" * 80 + "\n")
            for r in rows:
                f.write(f"Order: {r['list_order']} | ID: {r['id']}\n")
                f.write(f"  Group Header: {r['group_header']}\n")
                f.write(f"  Article Num:  {r['article_num']}\n")
                f.write(f"  Article Label:{r['article_label']}\n")
                f.write(f"  Article Title:{r['article_title']}\n")
                f.write(f"  Section Label:{r['section_label']}\n")
                if r['structural_map']:
                     f.write(f"  Structural Map: {json.dumps(r['structural_map'])}\n")
                f.write("-" * 40 + "\n")
                
        print("Dump complete: const_hierarchy_dump.txt")
        cur.close()
        conn.close()
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    dump_hierarchy()
