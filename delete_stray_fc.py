import sys
import os
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
try:
    cur.execute("DELETE FROM fc_codal WHERE article_num NOT LIKE 'FC-%' RETURNING article_num")
    deleted = cur.fetchall()
    conn.commit()
    print(f"Deleted {len(deleted)} stray rows from fc_codal!")
except Exception as e:
    conn.rollback()
    print("Error:", e)
