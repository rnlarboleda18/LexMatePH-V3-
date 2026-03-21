
import psycopg2

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def main():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Query to specifically target the records requested
    query = """
        DELETE FROM sc_decided_cases 
        WHERE full_text_md IS NOT NULL 
          AND full_text_md != ''
          AND (case_number IS NULL OR case_number = '')
    """
    
    print(f"Executing deletion: {query}")
    cur.execute(query)
    deleted_count = cur.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Successfully deleted {deleted_count} rows.")

if __name__ == "__main__":
    main()
