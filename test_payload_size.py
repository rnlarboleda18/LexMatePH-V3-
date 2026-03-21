import psycopg2
from psycopg2.extras import RealDictCursor
import json
import sys
import os

# Import connection string safely
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from api.db_pool import DB_CONNECTION_STRING

def measure_payload(short_name, table_name=None):
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        target_table = table_name or f"{short_name.lower()}_codal"
        if short_name.upper() == 'CONST':
            target_table = 'consti_codal'
            
        print(f"\n--- Testing {short_name.upper()} ({target_table}) ---")
        
        # Get all columns for maximum realism
        cur.execute(f"SELECT * FROM {target_table} ORDER BY id ASC LIMIT 500") # Limit to avoid crashing memory if huge
        results = cur.fetchall()
        
        # Convert to JSON and measure
        json_str = json.dumps(results, default=str)
        size_bytes = len(json_str.encode('utf-8'))
        
        print(f"Row Count sample: {len(results)}")
        print(f"Sample Payload Size: {size_bytes / 1024:.2f} KB")
        
        # Now get full count to estimate total size
        cur.execute(f"SELECT COUNT(*) FROM {target_table}")
        total_rows = cur.fetchone()['count']
        
        if len(results) > 0:
             estimated_total = (size_bytes / len(results)) * total_rows
             print(f"Total Rows: {total_rows}")
             print(f"Estimated Total Payload Size: {estimated_total / (1024*1024):.2f} MB")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error measuring {short_name}: {e}")

if __name__ == "__main__":
    for code in ['RPC', 'CIV', 'CONST']:
         measure_payload(code)
