import json
import psycopg

# Load database connection
settings = json.load(open('api/local.settings.json'))
conn_str = settings['Values']['DB_CONNECTION_STRING']

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        # Get En Banc cases by model
        cur.execute("""
            SELECT ai_model, COUNT(*) 
            FROM sc_decided_cases 
            WHERE division LIKE '%En Banc%' 
            AND ai_model IS NOT NULL 
            GROUP BY ai_model 
            ORDER BY COUNT(*) DESC
        """)
        
        print("=" * 70)
        print("EN BANC CASES BY AI MODEL")
        print("=" * 70)
        print()
        
        results = cur.fetchall()
        for model, count in results:
            print(f"{model:40} {count:>10,} cases")
        
        print()
        print("=" * 70)
        
        # Get total En Banc cases
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE division LIKE '%En Banc%'")
        total = cur.fetchone()[0]
        
        # Get undigested En Banc
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE division LIKE '%En Banc%' AND ai_model IS NULL")
        undigested = cur.fetchone()[0]
        
        print(f"{'TOTAL En Banc Cases':40} {total:>10,}")
        print(f"{'Undigested (NULL model)':40} {undigested:>10,}")
        print("=" * 70)
