import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT content_md, article_title FROM fc_codal WHERE article_num IN ('FC-I-7', 'FC-I-8')")
for r in cur.fetchall():
    print("Title:", repr(r[1]))
    print("Content ends with:", repr(r[0][-30:]))
