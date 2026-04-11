import csv
import sys
import os
import json

# Add the 'api' directory to block path so we can import db_pool
sys.path.insert(0, os.path.abspath('api'))

# Read DB_CONNECTION_STRING from local.settings.json
settings_path = os.path.join('api', 'local.settings.json')
try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)
        db_string = settings.get("Values", {}).get("DB_CONNECTION_STRING")
        if db_string:
            os.environ["LOCAL_DB_CONNECTION_STRING"] = db_string
except Exception as e:
    print(f"Failed to read local.settings.json: {e}")

os.environ['ENVIRONMENT'] = 'local'

from db_pool import get_db_conn

def export_rpc():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            # Query all data from rpc_codal, ordered by id
            cur.execute("SELECT * FROM rpc_codal ORDER BY id;")
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    filename = "rpc_codal_backup_before_fidelity.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
        
    print(f"Successfully exported {len(rows)} rows to {filename}")

if __name__ == "__main__":
    export_rpc()
