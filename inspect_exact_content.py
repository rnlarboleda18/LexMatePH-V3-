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

def inspect_exact_content():
    conn_str = get_conn_str()
    if not conn_str:
        return
        
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("--- CONTENT FOR I-0 (Article I) ---")
        cur.execute("SELECT id, article_num, article_title, content_md, group_header FROM const_codal WHERE article_num = 'I-0'")
        row1 = cur.fetchone()
        if row1:
            print(f"ID: {row1['id']}")
            print(f"Num: {row1['article_num']}")
            print(f"Title: {row1['article_title']}")
            print(f"Group: {row1['group_header']}")
            print(f"Content: {row1['content_md'][:300]}...")
        else:
            print("Row 'I-0' not found")
            
        print("\n--- CONTENT FOR II-0 (Article II) ---")
        cur.execute("SELECT id, article_num, article_title, content_md, group_header FROM const_codal WHERE article_num = 'II-0'")
        row2 = cur.fetchone()
        if row2:
            print(f"ID: {row2['id']}")
            print(f"Num: {row2['article_num']}")
            print(f"Title: {row2['article_title']}")
            print(f"Group: {row2['group_header']}")
            print(f"Content: {row2['content_md'][:300]}...")
        else:
             print("Row 'II-0' not found")
             
        # Check for absolute duplicates or weird strings
        print("\n--- ANY ROW WITH 'National Territory' IN TITLE ---")
        cur.execute("SELECT id, article_num, article_title FROM const_codal WHERE article_title ILIKE '%National Territory%'")
        rows = cur.fetchall()
        for r in rows:
            print(f"ID: {r['id']} | Num: {r['article_num']} | Title: {r['article_title']}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_exact_content()
