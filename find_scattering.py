import psycopg2

conn = psycopg2.connect('postgresql://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require')
cur = conn.cursor()

# Search for potential markers in questions AND answers
# Looking for: (a), (b), a., b., Q1a, A1a
print("Searching for markers...")
cur.execute("""
    SELECT q.id, q.year, q.subject, q.text, a.text 
    FROM questions q
    JOIN answers a ON q.id = a.question_id
    WHERE q.text ~ '^\\\\([a-z]\\\\)|^Q\\\\d|^[a-z]\\\\.' 
       OR a.text ~ '^\\\\([a-z]\\\\)|^A\\\\d|^[a-z]\\\\.'
    ORDER BY q.year DESC, q.subject, q.id
    LIMIT 100
""")

rows = cur.fetchall()
for r in rows:
    print(f"ID:{r[0]} | {r[1]} {r[2]} | Q: {r[3][:60]} | A: {r[4][:60]}")

cur.close()
conn.close()
