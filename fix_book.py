import sys
import os
import psycopg2
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

def fix_book_code(conn, is_cloud=False):
    cur = conn.cursor()
    cur.execute("UPDATE fc_codal SET book_code = 'FC' WHERE article_num = 'FC-I-8'")
    conn.commit()
    print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Updated book_code for FC-I-8.")

try:
    lconn = get_db_connection()
    fix_book_code(lconn, False)
    lconn.close()
except Exception as e:
    print("Local error:", e)

try:
    CLOUD_DSN = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
    cconn = psycopg2.connect(CLOUD_DSN)
    fix_book_code(cconn, True)
    cconn.close()
except Exception as e:
    print("Cloud error:", e)
