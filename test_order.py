import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT list_order, article_num, content_md FROM fc_codal WHERE list_order BETWEEN 328 AND 331 ORDER BY list_order")
for r in cur.fetchall():
    print(f"order={r[0]}, num={repr(r[1])}, content={repr(r[2][:30]) if r[2] else None}")
