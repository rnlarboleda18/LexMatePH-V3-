import psycopg2

conn = psycopg2.connect('postgresql://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require')
cur = conn.cursor()

# Check for Q1a, A1a patterns
cur.execute("""
    SELECT q.year, q.subject, q.text, a.text 
    FROM questions q
    JOIN answers a ON q.id = a.question_id
    WHERE q.text ~* '^Q\\d+' OR a.text ~* '^A\\d+'
    ORDER BY q.year DESC, q.id
    LIMIT 50
""")

rows = cur.fetchall()
for r in rows:
    year = r[0]
    subject = r[1]
    q_text = r[2][:50].replace('\n', ' ')
    a_text = r[3][:50].replace('\n', ' ')
    print(f"{year} | {subject} | Q: {q_text} | A: {a_text}")

cur.close()
conn.close()
