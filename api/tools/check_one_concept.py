import psycopg2
import json

conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def check_one_concept():
    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        cur.execute("SELECT legal_concepts FROM sc_decided_cases WHERE legal_concepts IS NOT NULL LIMIT 1")
        res = cur.fetchone()
        if res:
            print(json.dumps(res[0][0], indent=2))
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_one_concept()
