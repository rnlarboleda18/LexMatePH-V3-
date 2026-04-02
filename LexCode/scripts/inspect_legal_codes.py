import psycopg2

conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'legal_codes'
""")
print("\nColumns in legal_codes:")
for row in cur.fetchall():
    print(row[0])
    
conn.close()
