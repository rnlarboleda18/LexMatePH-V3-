import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'fc' OR short_name = 'FC'")
code_id = cur.fetchone()[0]

cur.execute("SELECT version_id, article_number, content FROM article_versions WHERE code_id = %s AND article_number IN ('7', '8')", (code_id,))
for r in cur.fetchall():
    print(r[0], r[1])
    print(repr(r[2][:80]))

conn.close()
