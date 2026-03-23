import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

content_id = "8"
table = "fc_codal"
cols = "article_num, article_title, content_md, section_label"

cid_str = str(content_id).strip()
search_patterns = [str(content_id), f"%-{cid_str}"]

conn = get_db_connection()
cur = conn.cursor()

for pattern in search_patterns:
    op = "LIKE" if "%" in pattern else "="
    cur.execute(f"SELECT {cols} FROM {table} WHERE article_num {op} %s LIMIT 1", (pattern,))
    row = cur.fetchone()
    print(f"Pattern {pattern!r} matched row:", row is not None)
    if row:
        print("Row:", row)
        break

if not row:
    print("Trying Strategy B...")
    cur.execute("SELECT article_number, content FROM article_versions WHERE version_id::text = %s", (str(content_id),))
    row2 = cur.fetchone()
    if row2:
        print("Strategy B found:", row2)
    else:
        print("Strategy B nothing")
