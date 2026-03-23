import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT article_num FROM fc_codal WHERE article_num LIKE '%-%'")
rows = cur.fetchall()
print(f"FC_CODAL has {len(rows)} with hyphen. Examples:")
print([r[0] for r in rows[:20]])
