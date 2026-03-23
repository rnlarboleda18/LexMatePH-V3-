import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT article_num, article_label, article_title, section_label FROM fc_codal WHERE article_num IN ('FC-I-7', 'FC-I-8', 'FC-I-9')")
for r in cur.fetchall():
    print(f"Num: {r[0]}, Label: {repr(r[1])}, Title: {repr(r[2])}, Section: {repr(r[3])}")
