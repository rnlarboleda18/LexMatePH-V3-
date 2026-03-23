import psycopg2

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM codal_case_links WHERE provision_id LIKE 'Rule %%'")
        row = cur.fetchone()
        print(f"Total ROC Case Links found: {row[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
