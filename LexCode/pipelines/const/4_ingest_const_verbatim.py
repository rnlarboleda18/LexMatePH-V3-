"""
Ingest Constitution from 1987_Philippine_Constitution.md (Plain Text Verbatim) to DB (consti_codal)
Handles Article I (no sections) and Article headers with following titles.
"""
import re
import psycopg2
import os

DB_CONNECTION = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"
BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
MD_FILE_PATH = os.path.join(BASE_DIR, "LexCode", "Codals", "md", "1987_Philippine_Constitution.md")

def ingest_verbatim():
    print(f"Reading {MD_FILE_PATH}...")
    if not os.path.exists(MD_FILE_PATH):
        print(f"Error: File not found at {MD_FILE_PATH}")
        return

    with open(MD_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()

    print("Wiping consti_codal table...")
    cur.execute("TRUNCATE TABLE consti_codal;")

    # State machine variables
    current_art_label = None  # e.g. "ARTICLE I"
    current_art_num = None    # e.g. "I"
    current_art_title = None  # e.g. "NATIONAL TERRITORY"
    current_sec_label = None  # e.g. "SECTION 1."
    current_sec_num = None    # e.g. "1"
    current_body = []
    list_order = 0

    re_article = re.compile(r'^ARTICLE\s+([IVXLCDM]+)', re.IGNORECASE)
    re_section = re.compile(r'^SECTION\s+(\d+)\.', re.IGNORECASE)
    re_preamble = re.compile(r'^PREAMBLE', re.IGNORECASE)

    def flush_entry():
        nonlocal list_order
        body_text = "".join(current_body).strip()
        if not body_text and not current_sec_label:
            return

        # Special case for Article I or preamble where section might be missing
        final_sec_label = current_sec_label
        final_sec_num = current_sec_num
        
        if not final_sec_label and current_art_label:
             final_sec_label = current_art_label # Hoist article to section label if no section
             final_sec_num = "0"

        if final_sec_label:
            list_order += 1
            cur.execute("""
                INSERT INTO consti_codal (article_num, article_label, article_title, section_num, section_label, content_md, list_order, book_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'CONST')
            """, (
                current_art_num,
                current_art_label,
                current_art_title,
                final_sec_num,
                final_sec_label,
                body_text,
                list_order
            ))

    # Helper to detect Article Title (usually first non-empty line after ARTICLE X)
    finding_title = False

    for line in lines:
        stripped = line.strip()
        
        # 1. Preamble detection
        if re_preamble.match(stripped):
            flush_entry()
            current_art_label = "PREAMBLE"
            current_art_num = "0"
            current_art_title = "PREAMBLE"
            current_sec_label = "PREAMBLE"
            current_sec_num = "0"
            current_body = []
            continue

        # 2. Article detection
        art_match = re_article.match(stripped)
        if art_match:
            flush_entry()
            current_art_num = art_match.group(1).upper()
            current_art_label = f"ARTICLE {current_art_num}"
            current_art_title = None
            current_sec_label = None
            current_sec_num = None
            current_body = []
            finding_title = True
            continue

        if finding_title and stripped:
            current_art_title = stripped
            finding_title = False
            continue

        # 3. Section detection
        sec_match = re_section.match(stripped)
        if sec_match:
            flush_entry()
            current_sec_num = sec_match.group(1)
            current_sec_label = f"SECTION {current_sec_num}."
            current_body = [line] # Keep the original line with formatting
            continue

        # 4. Body collection
        if current_art_label:
            current_body.append(line)

    flush_entry() # Last one

    conn.commit()
    print(f"Ingested {list_order} entries into consti_codal.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    ingest_verbatim()
