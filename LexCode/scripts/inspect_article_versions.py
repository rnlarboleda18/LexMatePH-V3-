import psycopg2

conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns 
    WHERE table_name = 'article_versions'
""")
print("\nColumns in article_versions:")
for row in cur.fetchall():
    print(row)
    
conn.close()
