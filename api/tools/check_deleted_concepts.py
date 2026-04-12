import psycopg2

conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def count_duplicate_concepts():
    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        # This was my deduplication logic: find cases with same case_number and date but higher ID
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT 
                    jsonb_extract_path_text(concept, 'term') as term, 
                    jsonb_extract_path_text(concept, 'definition') as definition
                FROM sc_decided_cases, jsonb_array_elements(legal_concepts) as concept
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (PARTITION BY case_number, date ORDER BY id) as rn
                        FROM sc_decided_cases
                    ) t WHERE rn > 1
                )
            ) as sub
        """)
        # Wait, I already deleted them? No, that was in Turn 15.
        # If I already deleted them, they are gone from the table.
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    count_duplicate_concepts()
