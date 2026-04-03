import psycopg2

conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def count_unique_filtered():
    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT 
                    jsonb_extract_path_text(concept, 'term') as term, 
                    jsonb_extract_path_text(concept, 'definition') as definition
                FROM sc_decided_cases, jsonb_array_elements(legal_concepts) as concept
                WHERE date >= '1987-01-01' AND date <= '2025-12-31' 
                AND division = 'En Banc'
                AND legal_concepts IS NOT NULL
            ) as sub
        """)
        unique_count = cur.fetchone()[0]
        print(f"Unique concepts in En Banc 1987-2025 subset: {unique_count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    count_unique_filtered()
