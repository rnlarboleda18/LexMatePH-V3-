import psycopg2
from psycopg2.extras import RealDictCursor
import json
import re

# Cloud connection string
CLOUD_DB = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def natural_keys(text):
    if not text: return []
    return [ int(c) if c.isdigit() else c for c in re.split(r'(\d+)', str(text)) ]

def test_codex_mapping():
    print("Testing ROC mapping in codex logic style...")
    conn = psycopg2.connect(CLOUD_DB)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Simulate fetch from ROC table
        cur.execute("SELECT * FROM roc_codal LIMIT 5")
        rows = cur.fetchall()

        short_name = 'ROC'
        mapped_rows = []
        for r in rows:
            # Replicating the logic I just added to codex.py
            if short_name.upper() == 'ROC':
                book_lbl = r.get('part_title') or ""
                book_n = r.get('part_num')
                title_lbl = r.get('rule_title_full') or ""
                title_n = r.get('rule_num')
                chapter_lbl = r.get('group_1_title') or ""
                chapter_n = r.get('group_1_num')
                article_num = str(r.get('rule_section_label') or "")
            else:
                book_lbl = r.get('book_label') or ""
                book_n = r.get('book_num')
                article_num = str(r.get('article_num') or "")

            mapped_rows.append({
                "id": str(r['id']),
                "key_id": article_num,
                "article_number": article_num,
                "article_title": (r.get('section_title') or "") if short_name == 'ROC' else "",
                "group_header": r.get('group_2_title') or "",
                "book_label": book_lbl,
                "title_label": title_lbl
            })

        print("\nMapped Results (First 2):")
        for m in mapped_rows[:2]:
            print(json.dumps(m, indent=2))

        print("\nVerification: Success if 'article_number' starts with 'Rule' and 'book_label' is not empty.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_codex_mapping()
