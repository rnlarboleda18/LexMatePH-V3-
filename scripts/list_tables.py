import psycopg2

def list_tables():
    conn = psycopg2.connect('postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require')
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cur.fetchall()
    print("Tables in 'public' schema:")
    for t in tables:
        print(f"- {t[0]}")
    conn.close()

if __name__ == "__main__":
    list_tables()
