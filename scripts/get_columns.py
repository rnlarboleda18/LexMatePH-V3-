import psycopg2

def get_columns(table_name):
    conn = psycopg2.connect('postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require')
    cur = conn.cursor()
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
    columns = [row[0] for row in cur.fetchall()]
    print(f"{table_name} columns: {columns}")
    conn.close()

if __name__ == "__main__":
    get_columns('article_versions')
    get_columns('codal_amendments')
    get_columns('legal_codes')
