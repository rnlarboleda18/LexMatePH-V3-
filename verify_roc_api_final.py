import psycopg2
from psycopg2.extras import RealDictCursor
import json
import re

# Cloud connection string
CLOUD_DB = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def test_final_mapping():
    print("Testing FINAL ROC header mapping logic...")
    conn = psycopg2.connect(CLOUD_DB)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Simulate fetch from ROC table with aliases (mimicking roc.py)
        cur.execute("""
            SELECT *, 
                   part_num AS book,
                   part_title AS book_label,
                   rule_num AS title_num,
                   rule_title_full AS title_label,
                   group_1_title AS chapter_label,
                   group_2_title AS group_header,
                   rule_section_label AS article_num,
                   section_title AS article_title,
                   section_content AS content_md
            FROM roc_codal 
            LIMIT 1
        """)
        rows = cur.fetchall()

        print("\n--- Rows from roc.py style query ---")
        for r in rows:
            print(json.dumps(r, indent=2, default=str))

        # Simulate codex.py mapping logic
        print("\n--- Rows from codex.py style mapping ---")
        mapped_rows = []
        for r in rows:
            mapped_rows.append({
                "id": str(r['id']),
                "article_number": r['article_num'],
                "article_title": r['article_title'],
                "book": r['book'],
                "book_label": r['book_label'],
                "title_num": r['title_num'],
                "title_label": r['title_label'],
                "chapter_label": r['chapter_label'],
                "group_header": r['group_header'],
                "content": r['content_md'],
                "content_md": r['content_md'],
            })

        for m in mapped_rows:
            print(json.dumps(m, indent=2))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_final_mapping()
