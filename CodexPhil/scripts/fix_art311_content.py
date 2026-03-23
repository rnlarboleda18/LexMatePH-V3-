
import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "bar_db")
DB_USER = os.getenv("DB_USER", "postgres")
# Use the known correct password or fetch from env if set correctly elsewhere
DB_PASSWORD = os.getenv("DB_PASSWORD", "b66398241bfe483ba5b20ca5356a87be")

# Full text of Article 311 as amended by RA 10951 (cleaned of CHAPTER header)
CORRECT_CONTENT = """Article 311. Theft of the property of the National Library and National Museum. - If the property stolen be any property of the National Library or the National Museum, the penalty shall be arresto mayor or a fine ranging from Forty thousand pesos (P40,000) to One hundred thousand pesos (P100,000), or both, unless a higher penalty should be provided under other provisions of this Code, in which case, the offender shall be punished by such higher penalty."""

def fix_article_311():
    try:
        conn = psycopg2.connect("postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor()

        print("Updating Article 311 content...")
        cur.execute("""
            UPDATE article_versions
            SET content = %s
            WHERE article_number = '311' AND amendment_id = 'Republic Act No. 10951';
        """, (CORRECT_CONTENT,))
        
        conn.commit()
        print(f"Update successful. Rows affected: {cur.rowcount}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_article_311()
