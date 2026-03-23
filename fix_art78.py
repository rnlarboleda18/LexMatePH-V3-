import sys
import os
import psycopg2
sys.path.insert(0, os.path.abspath('api'))
from db_pool import get_db_connection

def fix_db(conn, is_cloud=False):
    cur = conn.cursor()
    cur.execute("SELECT id, content_md, article_title, section_label, created_at, updated_at FROM fc_codal WHERE article_num = 'FC-I-7'")
    row = cur.fetchone()
    if row:
        fc7_id, content_md, art_title, section_lbl, created_at, updated_at = row
        print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Found FC-I-7")
        if "8. " in content_md:
            print("Found '8. ' inside!")
            # let's split by '8. The marriage'
            parts = content_md.split("8. The marriage", 1)
            if len(parts) == 2:
                part7 = parts[0].strip()
                part8 = "The marriage" + parts[1]
                
                cur.execute("UPDATE fc_codal SET content_md = %s WHERE id = %s", (part7, fc7_id))
                
                cur.execute("SELECT id FROM fc_codal WHERE article_num = 'FC-I-8'")
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO fc_codal (article_num, article_title, content_md, section_label, created_at, updated_at) 
                        VALUES ('FC-I-8', %s, %s, %s, %s, %s)
                    """, (art_title, part8.strip(), section_lbl, created_at, updated_at))
                print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Split fc_codal FC-I-7 and FC-I-8.")
            
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'fc' OR short_name = 'FC'")
    code_row = cur.fetchone()
    if code_row:
        code_id = code_row[0]
        cur.execute("SELECT version_id, content, amendment_id, amendment_description, valid_from FROM article_versions WHERE code_id = %s AND article_number = '7'", (code_id,))
        for av_row in cur.fetchall():
            v_id, content, amd_id, amd_desc, valid_from = av_row
            if "8. The marriage" in content:
                parts = content.split("8. The marriage", 1)
                part7 = parts[0].strip()
                part8 = "The marriage" + parts[1]
                
                cur.execute("UPDATE article_versions SET content = %s WHERE version_id = %s", (part7, v_id))
                cur.execute("SELECT version_id FROM article_versions WHERE code_id = %s AND article_number = '8'", (code_id,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO article_versions (code_id, article_number, content, amendment_id, amendment_description, valid_from) VALUES (%s, '8', %s, %s, %s, %s)", (code_id, part8.strip(), amd_id, amd_desc, valid_from))
                print(f"[{'CLOUD' if is_cloud else 'LOCAL'}] Split article_versions 7 and 8.")
    conn.commit()

lconn = get_db_connection()
fix_db(lconn, False)
lconn.close()

CLOUD_DSN = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
cconn = psycopg2.connect(CLOUD_DSN)
fix_db(cconn, True)
cconn.close()
