import psycopg2

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'codal_case_links'
        """)
        rows = cur.fetchall()
        print("--- codal_case_links COLUMNS ---")
        for r in rows:
            print(f"Column: {r[0]} | Type: {r[1]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
