import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT id, article_num, content_md FROM fc_codal WHERE article_num LIKE '%-8'")
for r in cur.fetchall():
    print(r[0], r[1], repr(r[2][:50]), repr(r[2][-50:]))
conn.close()
