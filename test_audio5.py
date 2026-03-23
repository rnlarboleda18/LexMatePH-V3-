import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT article_num FROM fc_codal WHERE article_num = 'XVI-8' OR article_num = 'FC-8' OR article_num LIKE '%8%' LIMIT 10")
rows = cur.fetchall()
print("Rows matching 8 in fc_codal:")
for r in rows:
    print(r[0])
