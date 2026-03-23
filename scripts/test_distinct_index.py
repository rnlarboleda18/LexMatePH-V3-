import psycopg2

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor()
        
        cur.execute("SELECT DISTINCT target_paragraph_index FROM codal_case_links WHERE statute_id = 'ROC'")
        rows = cur.fetchall()
        print("--- DISTINCT target_paragraph_index for ROC ---")
        for r in rows:
            print(r)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
