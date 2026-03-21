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

def analyze_const():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Row count for CONST
        cur.execute("SELECT COUNT(*) FROM const_codal WHERE book_code = 'CONST'")
        count = cur.fetchone()['count']
        print(f"Total CONST rows: {count}")
        
        # 2. Check group headers for CONST
        print("\n--- CONST ROWS WITH GROUP HEADER ---")
        cur.execute("""
            SELECT id, list_order, article_label, article_title, section_label, group_header 
            FROM const_codal 
            WHERE book_code = 'CONST' AND group_header IS NOT NULL AND group_header != '' AND group_header != 'None'
            ORDER BY list_order
        """)
        rows = cur.fetchall()
        print(f"Total CONST rows with group header: {len(rows)}")
        for r in rows:
            print(f"Order: {r['list_order']} | {r['article_label']} | {r['section_label']} | Title: {r['article_title']} | Group: {r['group_header']}")
            
        # 3. Check for duplicates in CONST
        print("\n--- CONST DUPLICATES ---")
        cur.execute("""
            SELECT article_label, section_label, COUNT(*) as count 
            FROM const_codal 
            WHERE book_code = 'CONST'
            GROUP BY article_label, section_label 
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        dups = cur.fetchall()
        print(f"Found {len(dups)} duplicates")
        for d in dups:
            print(f"  {d['article_label']} | {d['section_label']} | Count: {d['count']}")
            
        # 4. Dump Article Titles in order
        print("\n--- CONST ARTICLE TITLES IN ORDER ---")
        cur.execute("""
            SELECT DISTINCT list_order, article_label, article_title 
            FROM const_codal 
            WHERE book_code = 'CONST' AND (section_label ILIKE 'ARTICLE%' OR article_num LIKE '%-0')
            ORDER BY list_order
        """)
        titles = cur.fetchall()
        for t in titles:
             print(f"Order: {t['list_order']} | {t['article_label']} | Title: {t['article_title']}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_const()
