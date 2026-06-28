import json
import psycopg2

def main():
    with open('api/local.settings.json') as f:
        settings = json.load(f)['Values']
        cloud_conn_str = settings['DB_CONNECTION_STRING']

    print('Connecting to Cloud DB...')
    try:
        conn = psycopg2.connect(cloud_conn_str)
        cur = conn.cursor()
        print('Querying for ID 72502...')
        cur.execute("SELECT id, case_number, date, full_title, sc_url FROM sc_decided_cases WHERE id = 72502")
        row = cur.fetchone()
        print('Result:', row)
        conn.close()
    except Exception as e:
        print('Error:', e)

if __name__ == '__main__':
    main()
