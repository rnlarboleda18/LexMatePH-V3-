import json
import psycopg2

def main():
    with open('api/local.settings.json') as f:
        settings = json.load(f)['Values']
        cloud_conn_str = settings['DB_CONNECTION_STRING']
        local_conn_str = settings['LOCAL_DB_CONNECTION_STRING']

    print('--- Searching Cloud ---')
    try:
        conn = psycopg2.connect(cloud_conn_str)
        cur = conn.cursor()
        cur.execute("SELECT id, case_number, date, full_title FROM sc_decided_cases WHERE case_number ILIKE %s OR full_title ILIKE %s", ('%Lupena%', '%Lupena%'))
        rows = cur.fetchall()
        print(f'Found {len(rows)} matching rows in Cloud:')
        for r in rows:
            print(r[0], r[1], r[2], r[3][:100] if r[3] else None)
        conn.close()
    except Exception as e:
        print('Cloud Error:', e)

    print('--- Searching Local ---')
    try:
        conn = psycopg2.connect(local_conn_str)
        cur = conn.cursor()
        cur.execute("SELECT id, case_number, date, full_title FROM sc_decided_cases WHERE case_number ILIKE %s OR full_title ILIKE %s", ('%Lupena%', '%Lupena%'))
        rows = cur.fetchall()
        print(f'Found {len(rows)} matching rows in Local:')
        for r in rows:
            print(r[0], r[1], r[2], r[3][:100] if r[3] else None)
        conn.close()
    except Exception as e:
        print('Local Error:', e)

if __name__ == '__main__':
    main()
