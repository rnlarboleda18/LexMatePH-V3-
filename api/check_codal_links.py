import psycopg2

conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def check_case_ids():
    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(DISTINCT case_id) FROM codal_case_links")
        unique_cases = cur.fetchone()[0]
        print(f"Unique case IDs in codal_case_links: {unique_cases}")
        
        cur.execute("SELECT COUNT(*) FROM codal_case_links")
        total_links = cur.fetchone()[0]
        print(f"Total links in codal_case_links: {total_links}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_case_ids()
