import sys
import os
import psycopg2
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

def fix_list_order(conn, is_cloud=False):
    cur = conn.cursor()
    # Find list_order of FC-I-7
    cur.execute("SELECT list_order, id FROM fc_codal WHERE article_num = 'FC-I-7'")
    row = cur.fetchone()
    if not row: return
    list_order_7, _ = row
    list_order_8 = list_order_7 + 1
    
    # Are there any empty article_nums?
    cur.execute("SELECT id, article_num, list_order FROM fc_codal WHERE article_num = '' OR article_num IS NULL")
    for r in cur.fetchall():
        print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Empty article_num found! id={r[0]}, order={r[2]}")
        cur.execute("DELETE FROM fc_codal WHERE id = %s", (r[0],))
        
    print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Shifting list_order...")
    cur.execute("UPDATE fc_codal SET list_order = list_order + 1 WHERE list_order >= %s", (list_order_8,))
    
    print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Setting FC-I-8 list_order to {list_order_8}")
    cur.execute("UPDATE fc_codal SET list_order = %s WHERE article_num = 'FC-I-8'", (list_order_8,))
    conn.commit()

# Local DB
try:
    lconn = get_db_connection()
    fix_list_order(lconn, False)
    lconn.close()
except Exception as e:
    print("Local error:", e)

# Cloud DB
try:
    CLOUD_DSN = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
    cconn = psycopg2.connect(CLOUD_DSN)
    fix_list_order(cconn, True)
    cconn.close()
except Exception as e:
    print("Cloud error:", e)
