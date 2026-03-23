import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "bar_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "b66398241bfe483ba5b20ca5356a87be")

def check_missing_descriptions():
    try:
        conn = psycopg2.connect("postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor()

        # Check Article 146 specifically
        print("Checking Article 146:")
        cur.execute("""
            SELECT article_number, amendment_id, right(content, 200)
            FROM article_versions 
            WHERE article_number = '315' AND amendment_id = 'Republic Act No. 10951';
        """)
        rows = cur.fetchall()
        for row in rows:
            print(row)

        # Check for any amended articles with missing descriptions
        print("\nChecking for all missing descriptions:")
        cur.execute("""
            SELECT count(*) 
            FROM article_versions 
            WHERE amendment_id IS NOT NULL 
            AND (amendment_description IS NULL OR amendment_description = '');
        """)
        count = cur.fetchone()[0]
        print(f"Total amended articles with missing descriptions: {count}")

        if count > 0:
             cur.execute("""
                SELECT article_number, amendment_id
                FROM article_versions 
                WHERE amendment_id IS NOT NULL 
                AND (amendment_description IS NULL OR amendment_description = '')
                LIMIT 10;
            """)
             print("Sample missing:")
             for row in cur.fetchall():
                 print(row)

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_missing_descriptions()
