import psycopg2
import json
import os

conn=psycopg2.connect(os.environ.get('DB_CONNECTION_STRING', 'postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db'))
cur=conn.cursor()

issuances = [
    "AM-07-9-12-SC", "AM-08-1-16-SC", "AM-09-6-8-SC", "AM-01-7-01-SC",
    "CPRA", "AM-02-8-13-SC", "NCJC", "RA-11642"
]

results = {}

for stat in issuances:
    cur.execute("""
        SELECT group_type, group_num, section_num 
        FROM sc_issuances_codal 
        WHERE statute_id = %s 
        ORDER BY sort_order 
        LIMIT 5
    """, (stat,))
    rows = cur.fetchall()
    results[stat] = rows

print(json.dumps(results, indent=2))
