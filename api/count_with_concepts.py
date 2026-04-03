import psycopg2

conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def count_concepts():
    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE legal_concepts IS NOT NULL AND jsonb_array_length(legal_concepts) > 0")
        count = cur.fetchone()[0]
        print(f"Rows with legal concepts: {count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    count_concepts()
