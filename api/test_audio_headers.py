import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from db_pool import get_db_connection, put_db_connection
from psycopg2.extras import RealDictCursor

def test_transition():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT content_md FROM consti_codal WHERE id = 227")
        row = cur.fetchone()
        if row:
            print("\n--- CONTENT_MD FOR ID 227 ---")
            print(row['content_md'])
    except Exception as e:
        print(f"Error: {e}")
    put_db_connection(conn)

test_transition()
