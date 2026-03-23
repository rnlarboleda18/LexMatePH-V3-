import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- fc_codal FC-I-8 ---")
cur.execute("SELECT content_md FROM fc_codal WHERE article_num = 'FC-I-8'")
for r in cur.fetchall():
    print(repr(r[0]))

print("--- article_versions 8 ---")
cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'FC'")
code_id = cur.fetchone()[0]
cur.execute("SELECT version_id, content, valid_from FROM article_versions WHERE code_id = %s AND article_number = '8'", (code_id,))
for r in cur.fetchall():
    print(repr(r[1]))

conn.close()
