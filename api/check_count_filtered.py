import psycopg2

conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def check_count_with_filter():
    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        table_name = 'sc_decided_cases'
        print("Checking En Banc count (1987-2025) with legal_concepts IS NOT NULL...")
        cur.execute(f"""
            SELECT COUNT(*) 
            FROM {table_name} 
            WHERE date >= '1987-01-01' AND date <= '2025-12-31' 
            AND (division = 'En Banc' OR division = 'EN BANC')
            AND legal_concepts IS NOT NULL
            AND jsonb_array_length(legal_concepts) > 0
        """)
        count = cur.fetchone()[0]
        print(f"Count with legal_concepts: {count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_count_with_filter()
