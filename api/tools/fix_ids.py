import json
import psycopg2

db = json.load(open('local.settings.json'))['Values']['DB_CONNECTION_STRING']
conn = psycopg2.connect(db)
cur = conn.cursor()
cur.execute("UPDATE statutes SET id = alias WHERE alias IN ('AM-07-9-12-SC', 'AM-08-1-16-SC', 'AM-09-6-8-SC', 'AM-01-7-01-SC', 'AM-02-8-13-SC', 'NCJC', 'RA-11642')")
conn.commit()
print("Statute IDs fixed!")
