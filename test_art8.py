import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT content_md FROM fc_codal WHERE article_num = 'FC-I-7'")
row = cur.fetchone()
if row:
    print(repr(row[0]))
else:
    print("Not found")
