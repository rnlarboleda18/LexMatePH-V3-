import psycopg2
import os

try:
    conn = psycopg2.connect(os.environ.get('DB_CONNECTION_STRING', 'postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db'))
    cur = conn.cursor()
    
    statutes = ('AM-07-9-12-SC', 'AM-08-1-16-SC', 'AM-09-6-8-SC', 'AM-01-7-01-SC', 'CPRA', 'AM-02-8-13-SC', 'NCJC', 'RA-11642')
    
    cur.execute("SELECT statute_id, COUNT(*) FROM codal_case_links WHERE statute_id IN %s GROUP BY statute_id", (statutes,))
    print('Links found:')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]}')
        
    cur.execute("SELECT COUNT(DISTINCT case_id) FROM codal_case_links WHERE statute_id IN %s", (statutes,))
    print(f'\nTotal unique cases linked: {cur.fetchone()[0]}')
    
except Exception as e:
    print(f"Error checking DB: {e}")
