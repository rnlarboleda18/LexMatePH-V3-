import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT content_md FROM fc_codal WHERE article_num = 'FC-I-8'")
content = cur.fetchone()[0]
print("--- FULL TEXT OF FC-I-8 ---")
print(content)
conn.close()
