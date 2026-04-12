import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from db_pool import get_db_connection, put_db_connection
from psycopg2.extras import RealDictCursor

def find_section7():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, article_num, section_label, content_md, list_order 
            FROM consti_codal 
            WHERE section_label ILIKE '%SECTION 7%' AND article_num = 'II'
        """)
        row = cur.fetchone()
        if row:
            print("\n--- FOUND ROW ---")
            for k, v in row.items():
                print(f"{k}: {v}")
            
            # Fetch preceding row
            list_order = row['list_order']
            cur.execute("""
                SELECT id, article_num, section_label, content_md, list_order 
                FROM consti_codal 
                WHERE list_order < %s 
                ORDER BY list_order DESC LIMIT 1
            """, (list_order,))
            prev = cur.fetchone()
            if prev:
                print("\n--- PREVIOUS ROW ---")
                for k, v in prev.items():
                    print(f"{k}: {v}")
                    
        else:
            print("Section 7 of Article II not found")
    except Exception as e:
        print(f"Error: {e}")
    put_db_connection(conn)

find_section7()
