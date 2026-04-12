import psycopg2
from psycopg2.extras import RealDictCursor
import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')
from db_pool import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT content_md FROM rpc_codal WHERE article_num = '11'")
    row = cur.fetchone()
    
    with open(r'c:\tmp\article11_subitems.txt', 'w', encoding='utf-8') as f:
        if row and row['content_md']:
             lines = row['content_md'].split('\n')
             for i, line in enumerate(lines):
                  f.write(f"[{i+1}] {repr(line)}\n")
        else:
             f.write("No content found")

except Exception as e:
    with open(r'c:\tmp\article11_subitems.txt', 'w', encoding='utf-8') as f:
         f.write(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
print("Saved filter contents")
