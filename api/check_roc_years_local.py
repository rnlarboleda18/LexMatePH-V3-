import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Using the local connection string found in the scripts
db_url = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

try:
    print(f"Connecting to LOCAL DB: {db_url.split('@')[1]}...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Distribution of ROC links by year
    cur.execute("""
        SELECT 
            EXTRACT(YEAR FROM s.date) as year,
            COUNT(*) as link_count
        FROM codal_case_links l 
        JOIN sc_decided_cases s ON l.case_id = s.id 
        WHERE l.statute_id = 'ROC'
        GROUP BY 1
        ORDER BY 1 DESC
    """)
    rows = cur.fetchall()
    print("ROC Links year distribution:")
    for row in rows:
        print(f"Year {int(row['year'])}: {row['link_count']} links")
    
    # 2. Max date for ROC links
    cur.execute("""
        SELECT MAX(s.date) as max_linked_date 
        FROM codal_case_links l 
        JOIN sc_decided_cases s ON l.case_id = s.id 
        WHERE l.statute_id = 'ROC'
    """)
    res2 = cur.fetchone()
    print(f"\nLatest ROC link date: {res2['max_linked_date']}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
