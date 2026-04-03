import os
import json
import psycopg2

def get_conn_str():
    try:
        path = 'api/local.settings.json'
        if not os.path.exists(path):
            path = 'local.settings.json'
        with open(path, 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception as e:
        print(f"Error reading config: {e}")
    return None

def check_all_table_counts():
    conn_str_cloud = get_conn_str()
    conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [t[0] for t in cur.fetchall()]
        
        print("Checking local table counts:")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            print(f"- {t}: {count}")
            # If any count matches 3114, help me out
            if count == 3114:
                print("   *** MATCH FOUND! ***")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_all_table_counts()
