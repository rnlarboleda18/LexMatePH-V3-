import psycopg2
import json
import os
import re

DB_URL = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
JSON_PATH = os.path.join(os.path.dirname(__file__), "roc_headers_extracted.json")

def clean_text(text):
    return text.replace("##", "").replace("###", "").strip()

def main():
    if not os.path.exists(JSON_PATH):
         print(f"Error: {JSON_PATH} missing.")
         return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
         data = json.load(f)

    print("Connecting to Cloud DB...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("Cleaning up broken spacer rows with empty article_num...")
    cur.execute("DELETE FROM roc_codal WHERE article_num = ''")
    print(f"  Deleted {cur.rowcount} empty spacers.")

    # File to Book mapping
    book_map = {
        "1. ROC Civil Procedure as amended 2019.md": {"label": "Civil Procedure", "num": 1},
        "2. ROC Special Proceeding.md": {"label": "Special Proceedings", "num": 2},
        "3. ROC Criminal Procedure.md": {"label": "Criminal Procedure", "num": 3},
        "4. ROC Evidence as amended 2019.md": {"label": "Evidence", "num": 4}
    }

    inserted_count = 0

    for filename, headers in data.items():
        if filename not in book_map:
             continue
             
        book_info = book_map[filename]
        print(f"\nProcessing headers for {book_info['label']}...")

        for h in headers:
            text = h['text'].strip()
            # Skip noise or Rule markers
            if "X X X" in text or "EFFECTIVENESS" in text or "RULE" in text.upper():
                 continue

            clean_title = clean_text(text)
            after_rule = h.get('after_rule')
            after_section = h.get('after_section')

            # Extract Rule number string e.g., "### RULE 130" -> "Rule 130"
            title_label = "Rule 1" # Fallback
            if after_rule:
                 match_rule = re.search(r'RULE\s+(\d+)', after_rule.upper())
                 if match_rule:
                      title_label = f"Rule {match_rule.group(1)}"

            # Subheaders inside a Rule vs Pre-Rule Subheaders
            if after_section:
                 section_num = int(after_section)
                 article_num = f"{title_label}, Section {after_section} - Header"
            else:
                 section_num = 0
                 article_num = f"{title_label}, Subheader"

            cur.execute("""
                INSERT INTO roc_codal (
                    id, book, book_label, title_label, section_num, 
                    article_num, article_title, content_md, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, %s,
                    %s, %s, %s, NOW(), NOW()
                )
            """, (
                book_info['num'], book_info['label'], title_label, section_num,
                article_num, clean_title, f"## {clean_title}"
            ))
            inserted_count += 1
            print(f"  Inserted spacer: {clean_title!r} at {article_num}")

    conn.commit()
    print(f"\n🎉 Successfully inserted {inserted_count} header spacers into Cloud `roc_codal`!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
