import re
import psycopg2
import uuid
import json

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"
MD_ARTICLES = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\Labor_Code_Articles.md"
MD_FOOTNOTES = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\Labor_Code_Footnotes.md"

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION)

def parse_roman_to_int(roman):
    if not roman: return None
    roman = roman.strip().upper().rstrip('.')
    roman_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
        'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
        'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20
    }
    if roman in roman_map: return roman_map[roman]
    try: return int(roman)
    except: return None

def load_footnotes():
    footnotes = {}
    with open(MD_FOOTNOTES, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^\[(\d+)\]\s*(.*)', line.strip())
            if m:
                val = int(m.group(1))
                if val <= 1000: # Filter out false positive matches like [7796] or [10911]
                    footnotes[str(val)] = m.group(2).strip()
    return footnotes

def ingest_labor():
    global_footnotes = load_footnotes()
    print(f"Loaded {len(global_footnotes)} footnotes.")

    with open(MD_ARTICLES, 'r', encoding='utf-8') as f:
        content = f.read()

    conn = get_db_connection()
    cur = conn.cursor()
    TABLE_NAME = "labor_codal"

    context = {
        'book_num': None, 'book_label': None,
        'title_num': None, 'title_label': None,
        'chapter_num': None, 'chapter_label': None
    }
    inserted_count = 0

    # Headers patterns — match the full line (strip ** markers), anchored to end-of-line
    pat_book    = re.compile(r'^##\s*\**Book\s+([a-zA-Z]+)\**\s*[-–]\s*\**([^*\n]+?)\**\s*$', re.IGNORECASE | re.MULTILINE)
    pat_title   = re.compile(r'^##\s*\**(Title|PRELIMINARY\s+TITLE)\s*([IVXLCDM0-9]*)\**\s*[–-]?\s*\**([^*\n]+?)\**\s*$', re.IGNORECASE | re.MULTILINE)
    pat_chapter = re.compile(r'^##\s*\**Chapter\s+([0-9IVX]+)\**\s*[–-]?\s*\**([^*\n]+?)\**\s*$', re.IGNORECASE | re.MULTILINE)
    
    # We will split the whole content by "ART. XX." or "ARTICLE XX."
    # The split will return chunks.
    # Group 1 = ART/ARTICLE, Group 2 = The Number, Group 3 = The Text after
    # But wait, re.split with groups returns: [text1, group1, group2, text2, group1, group2, text3...]
    chunks = re.split(r'\b(?:ART|ARTICLE)\.?\s+(\d+[A-Za-z\-]*)[\.]\s+', content, flags=re.IGNORECASE)

    try:
        cur.execute(f"TRUNCATE TABLE {TABLE_NAME};")

        # First chunk is prologue (everything before ART. 1)
        # We need to process it for headers
        def update_context(text):
            # Find last occurrence of headers in the text to set the current context
            # Or iterate all to update in order
            for m in pat_book.finditer(text):
                word_map = {'ONE':1,'TWO':2,'THREE':3,'FOUR':4,'FIVE':5,'SIX':6,'SEVEN':7,'EIGHT':8,'NINE':9,'TEN':10}
                val = parse_roman_to_int(m.group(1)) or word_map.get(m.group(1).upper())
                context.update({'book_num': val, 'book_label': m.group(2).strip(),
                                'title_num': None, 'title_label': None,
                                'chapter_num': None, 'chapter_label': None})
            for m in pat_title.finditer(text):
                if 'PRELIMINARY' in m.group(1).upper():
                    context.update({'title_num': 0, 'title_label': 'PRELIMINARY TITLE'})
                else:
                    context.update({'title_num': parse_roman_to_int(m.group(2)), 'title_label': m.group(3).strip()})
                context.update({'chapter_num': None, 'chapter_label': None})
            for m in pat_chapter.finditer(text):
                context.update({'chapter_num': parse_roman_to_int(m.group(1)), 'chapter_label': m.group(2).strip()})

        # Process first block (before Art 1)
        update_context(chunks[0])

        i = 1
        while i < len(chunks):
            art_num = chunks[i]
            # chunks[i+1] contains the rest of the text up to the next ART
            art_text_full = chunks[i+1]

            # In this text, first check if there's a bold title: e.g. "**Name of Decree.** – This..."
            # Note: There might be a header inside the text (e.g. Chapter II starts at the end of the text).
            # We MUST split the art_text_full into "Article body" and "Next Context Headers"
            # The article body goes up to the very first header. If there's no header, it's all body.
            headers_match = re.search(r'(?:^|\n)##\s*\**', art_text_full)
            if headers_match:
                body_part = art_text_full[:headers_match.start()]
                header_part = art_text_full[headers_match.start():]
            else:
                # wait, maybe header is on same line as next article?
                # e.g., "...body end.  ## **Chapter II - ...**" This will be matched by headers_match.
                body_part = art_text_full
                header_part = ""

            # Extract title if any from body_part.
            # Raw markdown looks like: **Title.** [2] – Body text
            # group(1) = any leading non-bold chars (usually empty/blank), group(2) = Title, group(3) = [2] – body...
            title_m = re.match(r'^([^*]{0,15}?)\*\*([^*]+?)\*\*[.\s]*(.*)', body_part, re.DOTALL)
            if title_m:
                art_title = title_m.group(2).strip().rstrip('.')
                raw_after_title = (title_m.group(3) or '').strip()

                # Sometimes a long title is split across two lines in the PDF-to-MD conversion,
                # leaving a continuation like "**Relations Commission.**" at the start of the body.
                # Detect and merge: if raw_after_title starts with **ShortTitle.** then merge into art_title.
                cont_m = re.match(r'^\*\*([^*]{1,80}?)\*\*[.]?\s*[\u2013\-]?\s*(.*)', raw_after_title, re.DOTALL)
                if cont_m and len(cont_m.group(1)) < 60:
                    art_title = f"{art_title} {cont_m.group(1).strip().rstrip('.')}"
                    raw_after_title = (cont_m.group(2) or '').strip()

                # The raw_after_title may start with: [2] – actual text  OR  – actual text  OR  actual text
                # We want to keep [N] markers in the body (so ArticleNode renders them as purple icons),
                # but strip the bare –/- dash that follows them.
                # Strip ONLY the dash/hyphen between marker(s) and body prose, keeping a space.
                body_txt = re.sub(r'^((?:\[\d+\]\s*)+)[\u2013\-]\s*', lambda m: m.group(1).rstrip() + ' ', raw_after_title)
                # If no marker, just strip a bare leading dash
                body_txt = re.sub(r'^[\u2013\-]\s*', '', body_txt).strip()
            else:
                art_title = ''
                body_txt = body_part.strip()


            # Deduce footnotes
            used_markers = re.findall(r'\[(\d+)\]', body_txt + art_title)
            article_fns = []
            for marker in sorted(set(used_markers), key=lambda x: int(x)):
                if marker in global_footnotes:
                    article_fns.append({'marker': marker, 'text': global_footnotes[marker]})
            footnotes_json = json.dumps(article_fns) if article_fns else None

            # Insert
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (
                    id, article_num, article_title, content_md,
                    book, book_label, title_num, title_label, chapter_num, chapter_label,
                    footnotes, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
            """, (
                str(uuid.uuid4()), art_num, art_title, body_txt,
                str(context['book_num']) if context['book_num'] else None, context['book_label'],
                str(context['title_num']) if context['title_num'] is not None else None, context['title_label'],
                str(context['chapter_num']) if context['chapter_num'] else None, context['chapter_label'],
                footnotes_json
            ))
            inserted_count += 1

            # Update context for the NEXT article using header_part
            update_context(header_part)

            i += 2

        conn.commit()
        print(f"✅ Successfully inserted {inserted_count} articles into {TABLE_NAME}.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    ingest_labor()
