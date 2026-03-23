import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'fc' OR short_name = 'FC'")
code_id = cur.fetchone()[0]

cur.execute("SELECT article_number, content FROM article_versions WHERE code_id = %s AND article_number = '8'", (code_id,))
row = cur.fetchone()
print("Av 8 exact:", row is not None)

cur.execute("SELECT article_number, content FROM article_versions WHERE code_id = %s AND article_number = '7'", (code_id,))
row7 = cur.fetchone()
if row7:
    print("Av 7 found, content length:", len(row7[1]))
    if "8. The marriage" in row7[1]:
        print("Av 7 CONTAINS Article 8!")
