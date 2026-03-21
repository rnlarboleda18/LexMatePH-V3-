import psycopg2
import json

import os
db_url = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"
conn = psycopg2.connect(db_url)
cur = conn.cursor()

query = "UPDATE sc_decided_cases SET digest_significance = NULL WHERE digest_significance LIKE '%PROCESSING%'"
cur.execute(query)
conn.commit()
print(f"Cleaned up {cur.rowcount} stuck processing flags.")
conn.close()
