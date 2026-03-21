import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from api.db_pool import DB_CONNECTION_STRING

def check_db_content():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("Targeting Cloud DB for exact matches:")
        cur.execute("""
            SELECT id, article_num, article_label, article_title, group_header 
            FROM consti_codal 
            WHERE group_header IS NOT NULL 
               OR article_title IN ('Principles', 'State Policies', 'Common Provisions')
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"\nID: {r['id']}")
            print(f"  article_title: {repr(r['article_title'])}")
            print(f"  group_header:  {repr(r['group_header'])}")
        cur.close()
        conn.close()
    except Exception as e:
         print(e)

check_db_content()
