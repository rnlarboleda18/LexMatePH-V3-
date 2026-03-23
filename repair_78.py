import sys
import os
import psycopg2
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

def repair(conn, is_cloud):
    cur = conn.cursor()
    # Get good text
    cur.execute("SELECT content_md FROM fc_codal WHERE article_num = 'FC-I-7'")
    t7 = cur.fetchone()[0]
    cur.execute("SELECT content_md FROM fc_codal WHERE article_num = 'FC-I-8'")
    t8 = cur.fetchone()[0]

    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'fc' OR short_name = 'FC'")
    code_id = cur.fetchone()[0]
    
    # Update article 7
    cur.execute("UPDATE article_versions SET content = %s WHERE code_id = %s AND article_number = '7'", (t7.strip(), code_id))
    # Update article 8
    cur.execute("UPDATE article_versions SET content = %s WHERE code_id = %s AND article_number = '8'", (t8.strip(), code_id))
    
    conn.commit()
    print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Repaired Article 7 and 8.")

lconn = get_db_connection()
repair(lconn, False)
lconn.close()

CLOUD_DSN = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
try:
    cconn = psycopg2.connect(CLOUD_DSN)
    repair(cconn, True)
    cconn.close()
except Exception as e:
    print("Could not connect to cloud DB:", e)
