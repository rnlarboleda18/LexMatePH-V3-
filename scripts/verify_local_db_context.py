import psycopg2
import json

def main():
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception as e:
        print(f"Error reading local.settings.json: {e}")
        return

    print(f"Connecting to Local DB with: {conn_str}")
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM roc_codal")
        count = cur.fetchone()[0]
        print(f"📊 Total ROC rows in Local DB: {count}")

        # Check for Rule 22 subheaders
        cur.execute("""
            SELECT title_label, section_num, article_num, article_title 
            FROM roc_codal 
            WHERE title_label = 'Rule 22' 
            ORDER BY section_num ASC
        """)
        rows = cur.fetchall()
        print("\n--- Rule 22 Rows in Local DB ---")
        for r in rows:
             print(f"  {r}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting to local DB: {e}")

if __name__ == "__main__":
    main()
