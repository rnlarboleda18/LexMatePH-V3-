
import psycopg2
import os
import json

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def sample():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    # Fetch 50 RPC provisions to check for paragraph patterns
    cur.execute("""
        SELECT jsonb_array_elements(statutes_involved)->>'provision' as prov
        FROM sc_decided_cases 
        WHERE statutes_involved IS NOT NULL 
          AND statutes_involved::text ILIKE '%Revised Penal Code%'
        LIMIT 200
    """)
    rows = [r[0] for r in cur.fetchall()]
    
    # Filter for interesting ones
    interesting = [r for r in rows if r and ('par' in r.lower() or 'no.' in r.lower() or '(' in r)]
    
    print("--- SAMPLE RPC PROVISIONS WITH PARAGRAPHS ---")
    for r in interesting[:20]:
        print(f"  {r}")
        
    conn.close()

if __name__ == "__main__":
    sample()
