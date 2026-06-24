import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    settings_path = 'local.settings.json'
    if not os.path.exists(settings_path):
        settings_path = '../local.settings.json'
    if not os.path.exists(settings_path):
        settings_path = 'api/local.settings.json'
        
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)
            conn_str = settings['Values'].get('DB_CONNECTION_STRING')
            if conn_str:
                return psycopg2.connect(conn_str)
                
    raise Exception("Could not find DB_CONNECTION_STRING")

def check_cases():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        print("Searching for cases containing 'Lupena' or 'Medina' on Cloud:")
        cur.execute("""
            SELECT id, case_number, short_title, date, sc_url, full_title, main_doctrine, significance_category, subject, ai_model
            FROM sc_decided_cases 
            WHERE case_number ILIKE '%Lupena%' 
               OR short_title ILIKE '%Lupena%'
               OR full_title ILIKE '%Lupena%'
               OR short_title ILIKE '%Medina%'
               OR full_title ILIKE '%Medina%'
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} matching rows:")
        for idx, row in enumerate(rows, 1):
            print(f"{idx}. ID: {row['id']}")
            print(f"   Case Number: {row['case_number']}")
            print(f"   Short Title: {row['short_title']}")
            print(f"   Date: {row['date']}")
            print(f"   URL: {row['sc_url']}")
            print(f"   Full Title: {row['full_title'][:150] if row['full_title'] else None}")
            print(f"   Main Doctrine: {row['main_doctrine'][:200] if row['main_doctrine'] else None}")
            print(f"   Significance: {row['significance_category']}")
            print(f"   AI Model: {row['ai_model']}")
            print("-" * 50)
            
    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_cases()
