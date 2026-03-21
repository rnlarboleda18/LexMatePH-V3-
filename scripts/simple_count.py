import psycopg2
import os

CONN_STR = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

try:
    conn = psycopg2.connect(CONN_STR)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM supreme_decisions WHERE main_doctrine IS NOT NULL")
    print(f"Digested Count: {cur.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(e)
