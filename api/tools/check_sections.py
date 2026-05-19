import psycopg2
import json
import os

conn=psycopg2.connect(os.environ.get('DB_CONNECTION_STRING', 'postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db'))
cur=conn.cursor()
cur.execute("SELECT statute_id, section_num, group_type, group_num FROM sc_issuances_codal WHERE statute_id IN ('CPRA', 'AM-09-6-8-SC', 'RA-11642') ORDER BY sort_order LIMIT 30")
rows = cur.fetchall()
print(json.dumps(rows, indent=2))
