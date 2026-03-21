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

def analyze_structure():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Unique Book Codes
        print("--- UNIQUE BOOK CODES ---")
        cur.execute("SELECT DISTINCT book_code FROM const_codal")
        for r in cur.fetchall(): print(f"  {r['book_code']}")
        
        # 2. Rows with Group Header
        print("\n--- ROWS WITH GROUP HEADER ---")
        cur.execute("""
            SELECT id, list_order, article_label, article_title, section_label, group_header 
            FROM const_codal 
            WHERE group_header IS NOT NULL AND group_header != '' AND group_header != 'None'
            ORDER BY list_order
        """)
        rows = cur.fetchall()
        print(f"Total rows with group header: {len(rows)}")
        for r in rows:
            print(f"Order: {r['list_order']} | {r['article_label']} | {r['section_label']} | Group: {r['group_header']}")
            
        # 3. Check for duplicates (same Article + Section)
        print("\n--- CHECKING FOR DUPLICATES ---")
        cur.execute("""
            SELECT article_label, section_label, COUNT(*) as count 
            FROM const_codal 
            GROUP BY article_label, section_label 
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        dups = cur.fetchall()
        print(f"Found {len(dups)} duplicates")
        for d in dups:
            print(f"  {d['article_label']} | {d['section_label']} | Count: {d['count']}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_structure()
