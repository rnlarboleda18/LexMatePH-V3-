import psycopg2
from psycopg2.extras import RealDictCursor

LOCAL_URL = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
CLOUD_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Comparing Rule 128, Section 1 titles...")
    
    # 1. Check Local
    try:
         conn_local = psycopg2.connect(LOCAL_URL)
         cur_local = conn_local.cursor(cursor_factory=RealDictCursor)
         cur_local.execute("SELECT article_title FROM roc_codal WHERE article_num = 'Rule 128, Section 1'")
         row_local = cur_local.fetchone()
         cur_local.close()
         conn_local.close()
         print(f"Local article_title: {row_local['article_title'] if row_local else 'NotFound'}")
    except Exception as e:
         print(f"Local DB Error: {e}")

    # 2. Check Cloud
    try:
         conn_cloud = psycopg2.connect(CLOUD_URL)
         cur_cloud = conn_cloud.cursor(cursor_factory=RealDictCursor)
         cur_cloud.execute("SELECT article_title FROM roc_codal WHERE article_num = 'Rule 128, Section 1'")
         row_cloud = cur_cloud.fetchone()
         cur_cloud.close()
         conn_cloud.close()
         print(f"Cloud article_title: {row_cloud['article_title'] if row_cloud else 'NotFound'}")
    except Exception as e:
         print(f"Cloud DB Error: {e}")

if __name__ == "__main__":
    main()
