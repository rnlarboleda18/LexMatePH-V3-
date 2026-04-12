import psycopg2
from psycopg2.extras import RealDictCursor
import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')
from db_pool import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT content_md FROM rpc_codal WHERE article_num = '2'")
    row = cur.fetchone()
    if row and row['content_md']:
         print("=== ARTICLE 2 LINE BY LINE ===")
         lines = row['content_md'].split('\n')
         for i, line in enumerate(lines):
              print(f"[{i+1}] {repr(line)}")
    else:
         print("No content found")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
