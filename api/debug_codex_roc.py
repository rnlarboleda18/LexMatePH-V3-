import psycopg2
import json
import re
import os
from psycopg2.extras import RealDictCursor

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def clean_structural_label(label):
    if not label: return ""
    cleaned = re.sub(r'^(TITLE|CHAPTER)\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN)\s*:?\s*', '', label, flags=re.IGNORECASE)
    return cleaned.strip()

def natural_keys(text):
    if not text: return []
    return [ int(c) if c.isdigit() else c for c in re.split(r'(\d+)', str(text)) ]

def debug_roc():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        table_name = 'roc_codal'
        short_name = 'ROC'
        
        # Simulate query
        query = f"SELECT * FROM {table_name}"
        cur.execute(query)
        rows = cur.fetchall()
        print(f"Fetched {len(rows)} rows from {table_name}")

        has_list_order = False # from our inspection
        
        # Sort
        # rows.sort(key=lambda x: natural_keys(str(x['article_num']) if x['article_num'] else ""))
        # Wait, let's just run natural_keys sorting
        try:
             rows.sort(key=lambda x: natural_keys(str(x['article_num']) if x['article_num'] else ""))
        except Exception as e:
             print(f"Sorting error: {e}")
             return

        prev_book = None
        prev_title = None
        prev_chapter = None
        
        mapped_rows = []
        for i, r in enumerate(rows):
            try:
                content_to_send = r.get('content_md') or r.get('content') or ""
                article_num = str(r.get('article_num') or "")
                
                book_lbl = r.get('book_label') or ""
                title_lbl = clean_structural_label(r.get('title_label'))
                chapter_lbl = clean_structural_label(r.get('chapter_label'))

                injections = []
                if book_lbl and prev_book != book_lbl:
                    injections.append(f"## {book_lbl}")
                    prev_book = book_lbl
                if title_lbl and prev_title != title_lbl:
                    injections.append(f"## {title_lbl}")
                    prev_title = title_lbl
                if chapter_lbl and prev_chapter != chapter_lbl:
                    injections.append(f"## {chapter_lbl}")
                    prev_chapter = chapter_lbl

                if injections:
                    content_to_send = "\n\n".join(injections) + "\n\n" + content_to_send

                # Footnotes
                fn_json = r.get('footnotes')
                if fn_json:
                    fn_list = json.loads(fn_json) if isinstance(fn_json, str) else fn_json
                    if fn_list:
                         content_to_send += "\n\n---\n**Footnotes:**\n"

                mapped_rows.append({
                    "version_id": str(r['id']), 
                    "id": str(r['id']),
                    "key_id": str(r.get('article_num') or ""),
                    "article_number": article_num,
                    "content": content_to_send
                })

            except Exception as e:
                print(f"Error on row {i} (Article {r.get('article_num')}): {e}")
                return

        print("Successfully mapped rows!")

    except Exception as e:
        print(f"General Error: {e}")
    finally:
         conn.close()

if __name__ == "__main__":
    debug_roc()
