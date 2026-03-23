import sys
import os
import psycopg2
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

def fix_all(conn, is_cloud=False):
    cur = conn.cursor()
    # 1. Update article_label for FC-I-8 to 'TITLE I'
    cur.execute("UPDATE fc_codal SET article_label = 'TITLE I' WHERE article_num = 'FC-I-8'")
    
    # 2. Fix the trailing '\n\nArticle.' in FC-I-7
    cur.execute("UPDATE fc_codal SET content_md = REPLACE(content_md, '\n\nArticle.', '') WHERE article_num = 'FC-I-7'")
    
    # 3. Same for article_versions
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'fc' OR short_name = 'FC'")
    code_id = cur.fetchone()[0]
    
    cur.execute("UPDATE article_versions SET content = REPLACE(content, '\n\nArticle.', '') WHERE code_id = %s AND article_number = '7'", (code_id,))
    
    conn.commit()
    print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Metadata and text cleaned successfully.")

try:
    lconn = get_db_connection()
    fix_all(lconn, False)
    lconn.close()
except Exception as e:
    print("Local error:", e)

try:
    CLOUD_DSN = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
    cconn = psycopg2.connect(CLOUD_DSN)
    fix_all(cconn, True)
    cconn.close()
except Exception as e:
    print("Cloud error:", e)
