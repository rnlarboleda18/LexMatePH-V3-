import psycopg2

conn_str = "postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    # Check A. B. C. D. style MCQs
    cur.execute("SELECT COUNT(*) FROM questions WHERE text ~ ' B\\. '")
    dot_b = cur.fetchone()[0]
    
    # Check 1. 2. 3. style subquestions
    cur.execute("SELECT COUNT(*) FROM questions WHERE text ~ ' 2\\. '")
    dot_2 = cur.fetchone()[0]

    print(f"With ' B. ': {dot_b}")
    print(f"With ' 2. ': {dot_2}")
    
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
