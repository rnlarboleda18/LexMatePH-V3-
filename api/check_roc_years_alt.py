import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Using the connection string from fleet_stats.py which might have different firewall rules or proxy settings
db_url = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

try:
    print(f"Connecting to {db_url.split('@')[1]}...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Total count and max date in sc_decided_cases
    cur.execute("SELECT COUNT(*) as total, MAX(date) as max_date FROM sc_decided_cases")
    res = cur.fetchone()
    print(f"Case Data: {res}")
    
    # 2. Max date for ROC links
    cur.execute("""
        SELECT MAX(s.date) as max_linked_date 
        FROM codal_case_links l 
        JOIN sc_decided_cases s ON l.case_id = s.id 
        WHERE l.statute_id = 'ROC'
    """)
    res2 = cur.fetchone()
    print(f"ROC Linked Data: {res2}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
