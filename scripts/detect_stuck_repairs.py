import psycopg2

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def analyze_stuck_repairs():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print("Fetching stuck cases...")
    # Same logic as fleet_repair.py to identify targets
    cur.execute("""
        SELECT id, short_title, updated_at 
        FROM sc_decided_cases 
        WHERE updated_at >= DATE_TRUNC('day', NOW())
        AND (
            short_title ILIKE '%Judge%' 
            OR short_title ILIKE '%Justice%' 
            OR short_title ILIKE '%Fiscal%'
            OR short_title ILIKE '%Sheriff%'
            OR short_title ILIKE '%Atty.%'
            OR short_title ILIKE '%Governor%'
            OR short_title ILIKE '%Hon.%'
            OR short_title LIKE '%Ã%' 
            OR short_title LIKE '%Â%'
        )
        ORDER BY updated_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} stubborn cases.")
    print("-" * 50)
    for cid, title, updated in rows:
        print(f"ID {cid} | Last Update: {updated} | Title: {title}")
        
    conn.close()

if __name__ == "__main__":
    analyze_stuck_repairs()
