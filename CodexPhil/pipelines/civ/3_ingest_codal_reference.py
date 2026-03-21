import re
import psycopg2
import os
import uuid

# Configuration
DB_CONNECTION = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"
MD_FILE_PATH = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\CodexPhil\Codals\md\CIV_structured.md"

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION)

def parse_roman_to_int(roman):
    """Simple parser for common Roman numerals (I to L)."""
    if not roman: return None
    roman = roman.strip().upper().rstrip('.')
    
    # Direct Map
    roman_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
        'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
        'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20
    }
    if roman in roman_map: return roman_map[roman]
    
    # Try parsing Arabic just in case
    try:
        return int(roman)
    except:
        return None

def ingest_civ():
    print(f"Reading {MD_FILE_PATH}...")
    with open(MD_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Determine table
    TABLE_NAME = "civ_codal"
    
    # State Variables
    context = {
        'book_num': None,
        'book_label': None,
        'title_num': None,
        'title_label': None,
        'chapter_num': None,
        'chapter_label': None
    }
    
    current_article = {
        'num': None,
        'title': None,
        'body': [],
        'context': {}
    }
    
    inserted_count = 0

    # Regex Patterns (Adapted for CIV_structured.md where headers are ##)
    
    # ## BOOK I PERSONS
    pat_book = re.compile(r'^##\s+BOOK\s+([IVXLCDM]+|ONE|TWO)\s+(.*)', re.IGNORECASE)
    
    # ## TITLE I CIVIL PERSONALITY
    pat_title = re.compile(r'^##\s+(TITLE|PRELIMINARY TITLE)\s*([IVXLCDM0-9]*)\s*(.*)', re.IGNORECASE)
    
    # ## CHAPTER 1 General Provisions
    pat_chapter = re.compile(r'^##\s+CHAPTER\s+([0-9IVX]+)\s+(.*)', re.IGNORECASE)
    
    # ### Article 1. Title...
    pat_article = re.compile(r'^###\s+Article\s+([0-9A-Za-z\-]+)\.\s*(.*)', re.IGNORECASE)

    try:
        line_idx = 0
        for original_line in lines:
            line_idx += 1
            line = original_line.strip()
            
            # --- Helper to Flush ---
            def flush_current_article():
                if current_article['num'] is not None:
                     final_body = "".join(current_article['body']).strip()
                     # Insert into civ_codal
                     # Note: we use gen_random_uuid() for id if supported, else python uuid
                     
                     ctx = current_article['context']
                     article_title = current_article['title']
                     if not article_title:
                         # Try to extract title from body first line? No, usually body text starts immediately.
                         # Article 1 usually doesn't have a title in Civil Code, it just says "Article 1. This Act..."
                         # So article_title might remain empty or contain the first sentence.
                         pass

                     cur.execute(f"""
                        INSERT INTO {TABLE_NAME} (
                            id,
                            article_num,
                            article_title,
                            content_md,
                            book, book_label,
                            title_num, title_label,
                            chapter_num, chapter_label,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            NOW(), NOW()
                        )
                    """, (
                        str(uuid.uuid4()),
                        current_article['num'],
                        article_title,
                        final_body,
                        ctx.get('book_num'), ctx.get('book_label'),
                        ctx.get('title_num'), ctx.get('title_label'),
                        ctx.get('chapter_num'), ctx.get('chapter_label')
                    ))
                     return 1
                return 0

            # --- Header Matching ---

            # BOOK
            match = pat_book.match(line)
            if match:
                inserted_count += flush_current_article()
                current_article['num'] = None
                
                rom = match.group(1)
                lbl = match.group(2).strip()
                context['book_num'] = parse_roman_to_int(rom)
                context['book_label'] = lbl
                # Reset lower levels
                context['title_num'] = None
                context['title_label'] = None
                context['chapter_num'] = None
                context['chapter_label'] = None
                continue
                
            # TITLE
            match = pat_title.match(line)
            if match:
                inserted_count += flush_current_article()
                current_article['num'] = None
                
                type_str = match.group(1).upper()
                if "PRELIMINARY" in type_str:
                    context['title_num'] = 0
                    context['title_label'] = "PRELIMINARY TITLE"
                else:
                    rom = match.group(2)
                    lbl = match.group(3).strip()
                    context['title_num'] = parse_roman_to_int(rom)
                    context['title_label'] = lbl
                
                context['chapter_num'] = None
                context['chapter_label'] = None
                continue

            # CHAPTER
            match = pat_chapter.match(line)
            if match:
                inserted_count += flush_current_article()
                current_article['num'] = None
                
                num_str = match.group(1)
                lbl = match.group(2).strip()
                context['chapter_num'] = parse_roman_to_int(num_str)
                context['chapter_label'] = lbl
                continue

            # ARTICLE
            match = pat_article.match(line)
            if match:
                inserted_count += flush_current_article()
                
                current_article['num'] = match.group(1) # Text, e.g. "52"
                # The rest of the line is usually the body start, NOT a title.
                # In RPC, "Article 1. Time..." -> Title = Time when...
                # In CIV, "Article 1. This Act..." -> Title is None/Body.
                # We interpret group(2) as Body content, title is empty for now.
                
                body_start = match.group(2).strip()
                
                current_article['title'] = "" # Civil code articles rarely have named titles in the text
                current_article['body'] = [body_start + "\n" if body_start else ""]
                current_article['context'] = context.copy()
                continue
            
            # Body Content
            if current_article['num'] is not None:
                current_article['body'].append(original_line)
        
        # Flush last
        inserted_count += flush_current_article()
        
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
    ingest_civ()
