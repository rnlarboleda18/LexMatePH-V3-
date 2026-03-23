
import psycopg2

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def main():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print("Final DB Stats:")
    
    cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE full_text_md IS NOT NULL AND full_text_md != ''")
    total_md = cur.fetchone()[0]
    print(f"Total Records with Full Text: {total_md}")
    
    cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE scrape_source = 'ELib Unmatched Upload'")
    unmatched = cur.fetchone()[0]
    print(f"Remaining 'Unmatched' Records (New Inserts): {unmatched}")
    
    cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE scrape_source != 'ELib Unmatched Upload' AND full_text_md IS NOT NULL AND full_text_md != ''")
    matched = cur.fetchone()[0]
    print(f"Total Matched/Original Records Populated: {matched}")
    
    conn.close()

if __name__ == "__main__":
    main()
