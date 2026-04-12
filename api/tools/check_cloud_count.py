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

def check_cloud_count():
    conn_str_cloud = get_conn_str()
    if not conn_str_cloud:
        return
        
    try:
        conn = psycopg2.connect(conn_str_cloud)
        cur = conn.cursor()
        
        table_name = 'sc_decided_cases'
        print("Checking Cloud En Banc count (1987-2025)...")
        cur.execute(f"""
            SELECT COUNT(*) 
            FROM {table_name} 
            WHERE date >= '1987-01-01' AND date <= '2025-12-31' 
            AND division = 'En Banc'
        """)
        count = cur.fetchone()[0]
        print(f"Total Cloud En Banc: {count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error checking cloud count: {e}")

if __name__ == "__main__":
    check_cloud_count()
