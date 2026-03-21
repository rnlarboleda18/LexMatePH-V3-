import psycopg2
from psycopg2.extras import RealDictCursor

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Let's first inspect rows to see what is ACTUALLY in there!
        cur.execute("SELECT statute_id, provision_id, target_paragraph_index FROM codal_case_links WHERE statute_id = 'ROC' LIMIT 5")
        rows = cur.fetchall()
        print("--- SAMPLE ROWS ---")
        for r in rows:
            print(r)
            
        cur.execute("SELECT COUNT(*) FROM codal_case_links WHERE statute_id = 'ROC'")
        cnt = cur.fetchone()['count']
        print(f"Total ROC links: {cnt}")

        if cnt == 0:
            print("Zero links with statute_id = 'ROC' found!")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
