
import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "bar_db")
DB_USER = os.getenv("DB_USER", "postgres")
# Use the known correct password or fetch from env if set correctly elsewhere
DB_PASSWORD = os.getenv("DB_PASSWORD", "b66398241bfe483ba5b20ca5356a87be")

# Full text of Article 313 as amended by RA 10951 (cleaned of CHAPTER header)
CORRECT_CONTENT = """Article 313. Altering boundaries or landmarks. - Any person who shall alter the boundary marks or monuments of towns, provinces, or estates, or any other marks intended to designate the boundaries of the same, shall be punished by arresto menor or a fine not exceeding Twenty thousand pesos (P20,000), or both."""

def fix_article_313():
    try:
        conn = psycopg2.connect("postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor()

        print("Updating Article 313 content...")
        cur.execute("""
            UPDATE article_versions
            SET content = %s
            WHERE article_number = '313' AND amendment_id = 'Republic Act No. 10951';
        """, (CORRECT_CONTENT,))
        
        conn.commit()
        print(f"Update successful. Rows affected: {cur.rowcount}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_article_313()
