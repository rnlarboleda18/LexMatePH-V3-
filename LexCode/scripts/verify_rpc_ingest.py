import psycopg2
import json

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT article_number, content FROM article_versions WHERE code_id = '570b007a-36b6-4e74-a993-4b8d5d17a4ef' AND article_number = '114'")
row = cur.fetchone()
print(row)
conn.close()
