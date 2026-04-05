import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Try to load .env from the root if it exists
root_env = os.path.join(os.getcwd(), "..", ".env")
if os.path.exists(root_env):
    load_dotenv(root_env)

# Or local.settings.json from the api folder
local_settings = "local.settings.json"
import json
if os.path.exists(local_settings):
    with open(local_settings) as f:
        settings = json.load(f)
        if "Values" in settings and "DB_CONNECTION_STRING" in settings["Values"]:
            os.environ["DB_CONNECTION_STRING"] = settings["Values"]["DB_CONNECTION_STRING"]

db_url = os.environ.get("DB_CONNECTION_STRING")
if not db_url:
    print("DB_CONNECTION_STRING not found in environment")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Query for the range of years for ROC links
    cur.execute("""
        SELECT 
            MAX(s.date) as latest_case, 
            MIN(s.date) as earliest_case, 
            COUNT(*) as total_links,
            COUNT(DISTINCT l.case_id) as total_cases
        FROM codal_case_links l 
        JOIN sc_decided_cases s ON l.case_id = s.id 
        WHERE l.statute_id = 'ROC'
    """)
    result = cur.fetchone()
    print("ROC Linking Stats:")
    print(json.dumps(result, indent=2, default=str))
    
    # Also get a sample of recent cases to see the spread
    cur.execute("""
        SELECT DISTINCT s.short_title, s.date, s.case_id
        FROM codal_case_links l 
        JOIN sc_decided_cases s ON l.case_id = s.id 
        WHERE l.statute_id = 'ROC'
        ORDER BY s.date DESC
        LIMIT 5
    """)
    recent = cur.fetchall()
    print("\nMost Recent ROC-Linked Cases:")
    print(json.dumps(recent, indent=2, default=str))
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
