import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from db_pool import get_db_connection, put_db_connection
from psycopg2.extras import RealDictCursor

def find_all():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, article_num, article_label, article_title, section_label, content_md 
            FROM consti_codal 
            WHERE content_md ILIKE '%The Philippines is a democratic and republican State%'
        """)
        rows = cur.fetchall()
        print(f"\nFound {len(rows)} matching rows:")
        for r in rows:
            print("\n--- Row ---")
            for k, v in r.items():
                print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")
    put_db_connection(conn)

find_all()
