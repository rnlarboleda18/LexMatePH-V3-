import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from db_pool import get_db_connection, put_db_connection
from psycopg2.extras import RealDictCursor

def test_article2_section1():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM consti_codal WHERE article_num = 'II-1'")
        row = cur.fetchone()
        if row:
            print("\n--- ROW FOR II-1 ---")
            for k, v in row.items():
                print(f"{k}: {v}")
        else:
            print("Row II-1 not found")
    except Exception as e:
        print(f"Error: {e}")
    put_db_connection(conn)

test_article2_section1()
