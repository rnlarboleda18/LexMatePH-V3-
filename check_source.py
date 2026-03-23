import psycopg2
import json

conn_str = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    query = "SELECT source_url FROM answers WHERE text LIKE '%Q:%' LIMIT 5"
    cur.execute(query)
    sources = cur.fetchall()
    
    print("Sources from answers table:")
    for src in sources:
        print(src[0])
        
    query2 = "SELECT source_url FROM questions WHERE id IN (SELECT question_id FROM answers WHERE text LIKE '%Q:%') LIMIT 5"
    cur.execute(query2)
    sources2 = cur.fetchall()
    
    print("Sources from questions table:")
    for src in sources2:
        print(src[0])

except Exception as e:
    print("Error:", e)
