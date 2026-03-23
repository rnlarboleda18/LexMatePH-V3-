import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT article_num, content_md FROM fc_codal WHERE article_num LIKE '%8%' OR article_num = '8' LIMIT 5")
print("FC_CODAL matching '8':")
for row in cur.fetchall():
    print(f"Num: {row[0]}, Content: {row[1][:60]}...")
