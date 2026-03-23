import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT article_num FROM fc_codal WHERE article_num NOT LIKE 'FC-%' AND article_num != '0'")
rows = cur.fetchall()
print(f"Stray articles in fc_codal: {len(rows)}")
print([r[0] for r in rows])
