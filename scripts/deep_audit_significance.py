import psycopg2
import json
from datetime import datetime

def get_db_connection():
    with open('local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    return psycopg2.connect(conn_str)

def run_audit():
    conn = get_db_connection()
    cur = conn.cursor()

    ranges = [
        ("1901-1986", "date < '1987-01-01'"),
        ("1987-2025", "date >= '1987-01-01'")
    ]

    print("=== DEEP DB AUDIT: DIGESTION & SIGNIFICANCE ===")
    
    for label, date_filter in ranges:
        print(f"\n--- Era: {label} ---")
        
        # 1. Total Cases
        cur.execute(f"SELECT COUNT(*) FROM sc_decided_cases WHERE {date_filter}")
        total = cur.fetchone()[0]
        
        # 2. Undigested (Ghost)
        # Using digest_facts as proxy for digestion existence
        cur.execute(f"""
            SELECT COUNT(*) FROM sc_decided_cases 
            WHERE {date_filter} 
              AND (digest_facts IS NULL OR digest_facts::text = '{{}}' OR digest_facts::text = 'null')
              AND full_text_md IS NOT NULL
        """)
        ghosts = cur.fetchone()[0]

        # 3. No Classification / Significance
        # criteria: digested but digest_significance is NULL/empty OR significance_category inside json is missing
        # We rely on the top-level 'digest_significance' column if populated, or check the JSON.
        # Let's verify the 'digest_significance' column usage.
        
        cur.execute(f"""
            SELECT COUNT(*) FROM sc_decided_cases 
            WHERE {date_filter} 
              AND digest_facts IS NOT NULL
              AND (digest_significance IS NULL OR digest_significance = '' OR digest_significance = 'None')
        """)
        no_significance = cur.fetchone()[0]

        # 4. Weak AI Models (e.g. not the latest heavy hitters)
        # Check distribution of models for cases that HAVE content
        cur.execute(f"""
            SELECT ai_model, COUNT(*) 
            FROM sc_decided_cases 
            WHERE {date_filter} AND digest_facts IS NOT NULL
            GROUP BY ai_model 
            ORDER BY COUNT(*) DESC
        """)
        models = cur.fetchall()

        print(f"Total Cases: {total}")
        print(f"Undigested (Ghost): {ghosts}")
        print(f"Digested but NO Significance: {no_significance}")
        print("Model Breakdown:")
        for m, c in models:
            print(f"  - {m}: {c}")

    conn.close()

if __name__ == "__main__":
    run_audit()
