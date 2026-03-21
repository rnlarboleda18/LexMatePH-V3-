import psycopg2

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")
        cur = conn.cursor()
        cur.execute("""
            SELECT short_title, 
                   LENGTH(main_doctrine), 
                   LENGTH(digest_ratio), 
                   LENGTH(digest_ruling) 
            FROM sc_decided_cases 
            WHERE short_title ILIKE '%Tuazon v. Dela Cruz%'
        """)
        row = cur.fetchone()
        if row:
            print(f"Title: {row[0]}")
            print(f"Doctrine Len: {row[1]}")
            print(f"Ratio Len: {row[2]}")
            print(f"Ruling Len: {row[3]}")
        else:
            print("No case found for Tuazon v. Dela Cruz")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
