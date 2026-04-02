
import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "bar_db")
DB_USER = os.getenv("DB_USER", "postgres")
# Use the known correct password or fetch from env if set correctly elsewhere
DB_PASSWORD = os.getenv("DB_PASSWORD", "b66398241bfe483ba5b20ca5356a87be")

# Structural fix: Prepend Headers to the FIRST article of the new chapter.
# Article 312: Starts Chapter 4 (Usurpation)
# Article 314: Starts Chapter 5 (Culpable Insolvency)

def restore_chapter_headers():
    try:
        conn = psycopg2.connect("postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor()

        print("Restoring Chapter Headers...")

        # 1. Update Article 312 (Chapter 4)
        print("Restoring Chapter 4 Header to Article 312...")
        cur.execute("""
            UPDATE article_versions
            SET content = '## CHAPTER FOUR\n\n## USURPATION\n\n' || content
            WHERE article_number = '312' 
            AND amendment_id = 'Republic Act No. 10951'
            AND content NOT LIKE '## CHAPTER FOUR%';
        """)
        print(f"Article 312 updated. Rows affected: {cur.rowcount}")

        # 2. Update Article 314 (Chapter 5)
        print("Restoring Chapter 5 Header to Article 314...")
        cur.execute("""
             UPDATE article_versions
            SET content = '## CHAPTER FIVE\n\n## CULPABLE INSOLVENCY\n\n' || content
            WHERE article_number = '314' 
            AND amendment_id = 'Act No. 3815'
            AND content NOT LIKE '## CHAPTER FIVE%';
        """)
        print(f"Article 314 updated. Rows affected: {cur.rowcount}")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restore_chapter_headers()
