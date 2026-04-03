import psycopg2

conn_str_local = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def check_overlap():
    try:
        conn = psycopg2.connect(conn_str_local)
        cur = conn.cursor()
        
        # Count cases that are En Banc (1987-2025) AND have at least one link in codal_case_links
        cur.execute("""
            SELECT COUNT(DISTINCT s.id) 
            FROM sc_decided_cases s
            JOIN codal_case_links c ON s.id = c.case_id
            WHERE s.date >= '1987-01-01' AND s.date <= '2025-12-31' 
            AND s.division = 'En Banc'
        """)
        overlap_count = cur.fetchone()[0]
        print(f"En Banc (1987-2025) cases with codal links: {overlap_count}")
        
        # Count total unique cases in codal_case_links that are En Banc (any date)
        cur.execute("""
            SELECT COUNT(DISTINCT s.id) 
            FROM sc_decided_cases s
            JOIN codal_case_links c ON s.id = c.case_id
            WHERE s.division = 'En Banc'
        """)
        en_banc_links = cur.fetchone()[0]
        print(f"Total En Banc cases with codal links: {en_banc_links}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_overlap()
