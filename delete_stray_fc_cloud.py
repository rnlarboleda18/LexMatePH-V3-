import sys
import os
import psycopg2

CLOUD_DSN = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

conn = psycopg2.connect(CLOUD_DSN)
cur = conn.cursor()
try:
    cur.execute("DELETE FROM fc_codal WHERE article_num NOT LIKE 'FC-%'")
    deleted = cur.rowcount
    conn.commit()
    print(f"Deleted {deleted} stray rows from cloud fc_codal!")
except Exception as e:
    conn.rollback()
    print("Error on cloud:", e)
finally:
    conn.close()
