import re
import psycopg2
import os

# Configuration
DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"
MD_FILE_PATH = r"c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/data/LexCode/Codals/md/RPC_Verbatim_AI.md"

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION)

def parse_roman_to_int(roman):
    """Simple parser for common Roman numerals in RPC (I to XV usually)."""
    roman_map = {
        'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5,
        'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9, 'TEN': 10,
        'ELEVEN': 11, 'TWELVE': 12, 'THIRTEEN': 13, 'FOURTEEN': 14, 'FIFTEEN': 15,
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
    }
    # Clean up input
    clean_roman = roman.strip().upper().replace('.', '')
    return roman_map.get(clean_roman, None)

def ensure_schema(conn):
    """Ensures necessary columns exist in rpc_codal."""
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE rpc_codal ADD COLUMN IF NOT EXISTS chapter TEXT;")
        cur.execute("ALTER TABLE rpc_codal ADD COLUMN IF NOT EXISTS title_num INTEGER;")
        cur.execute("ALTER TABLE rpc_codal ADD COLUMN IF NOT EXISTS title_label TEXT;") # Ensure checking this too
        cur.execute("ALTER TABLE rpc_codal ADD COLUMN IF NOT EXISTS section_num INTEGER;") # Double check
        cur.execute("ALTER TABLE rpc_codal ADD COLUMN IF NOT EXISTS section_label TEXT;") # Double check
        conn.commit()
        print("Schema verified/updated.")
    except Exception as e:
        conn.rollback()
        print(f"Schema update failed: {e}")
    finally:
        cur.close()

def ingest_rpc():
    print(f"Reading {MD_FILE_PATH}...")
    with open(MD_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    conn = get_db_connection()
    ensure_schema(conn) # Run migration
    cur = conn.cursor()


    # State Variables
    context = {
        'book': None,
        'title': None,
        'chapter': None,
        'section_num': None,
        'section_label': None
    }
    
    current_article = {
        'num': None,
        'title': None,
        'body': [],
        'context': {}
    }
    
    updated_count = 0

    # Regex Patterns
    # Note: We use strict start anchors ^ to avoid false positives in body text
    # but the line might have whitespace, though MD headers shouldn't.
    
    # # BOOK ONE
    pat_book = re.compile(r'^# BOOK\s+(.*)', re.IGNORECASE)
    
    # ## TITLE ONE
    pat_title = re.compile(r'^## TITLE\s+(.*)', re.IGNORECASE)
    
    # ### CHAPTER ONE
    pat_chapter = re.compile(r'^### CHAPTER\s+(.*)', re.IGNORECASE)
    
    # #### SECTION ONE.-Label or SECTION ONE
    pat_section = re.compile(r'^#### SECTION\s+(.*)', re.IGNORECASE)
    
    # ##### Article 1. Title.
    pat_article = re.compile(r'^##### Article\s+(\d+)\.\s*(.*)', re.IGNORECASE)

    # Book map for text to int
    book_map = {
        'ONE': 1, 'TWO': 2, 'THREE': 3
    }

    try:
        line_idx = 0
        for original_line in lines:
            line_idx += 1
            line = original_line.strip()
            
            # --- Header Matching ---
            
            # Helper to flush current article if active
            def flush_current_article(lbl=""):
                if current_article['num'] is not None:
                     # Join raw lines (preserving source newlines)
                     final_body = "".join(current_article['body']).strip()
                     
                     if current_article['num'] == 2:
                        print(f"DEBUG: Flushing Article {current_article['num']} at event '{lbl}'")
                        print(f"DEBUG BODY END: {final_body[-100:]!r}")
                     cur.execute("""
                        UPDATE rpc_codal
                        SET 
                            article_title = %s,
                            content_md = %s,
                            book = %s,
                            title_label = %s,
                            title_num = %s,
                            chapter = %s,
                            section_num = %s,
                            section_label = %s
                        WHERE article_num = %s
                    """, (
                        current_article['title'],
                        final_body,
                        current_article['context'].get('book'),
                        current_article['context'].get('title'),
                        current_article['context'].get('title_num'),
                        current_article['context'].get('chapter'),
                        current_article['context'].get('section_num'),
                        current_article['context'].get('section_label'),
                        current_article['num']
                    ))
                     return 1
                return 0

            # BOOK
            match = pat_book.match(line)
            if match:
                updated_count += flush_current_article("BOOK")
                current_article['num'] = None # Stop capturing body for previous article
                
                raw_book = match.group(1).strip().upper()
                context['book'] = book_map.get(raw_book, 1)
                context['title'] = None
                context['title_num'] = None
                context['chapter'] = None
                context['section_num'] = None
                context['section_label'] = None
                continue
                
            # TITLE
            match = re.match(r'^##\s+(TITLE\s+.*|PRELIMINARY TITLE)', line, re.IGNORECASE)
            if match:
                updated_count += flush_current_article("TITLE")
                current_article['num'] = None # Stop capturing body
                
                raw_title_full = match.group(1).strip()
                context['title'] = raw_title_full
                if "PRELIMINARY" in raw_title_full.upper():
                    context['title_num'] = 0 
                else:
                    raw_num = re.sub(r'^TITLE\s+', '', raw_title_full, flags=re.IGNORECASE).strip()
                    context['title_num'] = parse_roman_to_int(raw_num) 
                
                context['chapter'] = None
                context['section_num'] = None
                context['section_label'] = None
                continue

            # CHAPTER
            match = pat_chapter.match(line)
            if match:
                updated_count += flush_current_article("CHAPTER")
                current_article['num'] = None # Stop capturing body
                
                context['chapter'] = f"CHAPTER {match.group(1).strip()}"
                context['section_num'] = None
                context['section_label'] = None
                continue
                
            # SECTION
            match = pat_section.match(line)
            if match:
                updated_count += flush_current_article("SECTION")
                current_article['num'] = None # Stop capturing body
                
                raw_section = match.group(1).strip()
                split_match = re.search(r'^([A-Z]+|I+|II+|III+|IV+|V+|VI+|VII+|VIII+|IX+|X+)\s*[\.\-]+\s*(.*)', raw_section, re.IGNORECASE)
                
                if split_match:
                    num_str = split_match.group(1)
                    label_str = split_match.group(2)
                    context['section_num'] = parse_roman_to_int(num_str)
                    context['section_label'] = label_str
                else:
                    context['section_num'] = parse_roman_to_int(raw_section)
                    context['section_label'] = None
                continue

            # ARTICLE
            match = pat_article.match(line)
            if match:
                # Flush Previous Article (if exists) -> Normally handled by headers now, but 
                # consecutive articles mean we still flush here.
                updated_count += flush_current_article("ARTICLE")
                
                # 2. Start New Article
                current_article['num'] = int(match.group(1))
                current_article['title'] = match.group(2).strip()
                current_article['body'] = []
                current_article['context'] = context.copy()
                continue
            
            # --- Body Content OR Header Descriptions ---
            
            if current_article['num'] is not None:
                # Normal Article Body -> Use ORIGINAL LINE (preserve whitespace, including blank lines)
                current_article['body'].append(original_line)
            
            elif line:
                # Floating text! Attach to deepest active context.
                # Only if line has content (skip blanks between headers)
                if context['section_num'] is not None:
                     if context['section_label']:
                         context['section_label'] += f" {line}"
                     else:
                         context['section_label'] = line
                elif context['chapter'] is not None:
                    context['chapter'] += f": {line}"
                elif context['title'] is not None:
                    context['title'] += f": {line}"


        # Flush Last Article
        if current_article['num'] is not None:
             final_body = "".join(current_article['body']).strip()
             cur.execute("""
                UPDATE rpc_codal
                SET 
                    article_title = %s,
                    content_md = %s,
                    book = %s,
                    title_label = %s,
                    title_num = %s,
                    chapter = %s,
                    section_num = %s,
                    section_label = %s
                WHERE article_num = %s
            """, (
                current_article['title'],
                final_body,
                current_article['context'].get('book'),
                current_article['context'].get('title'),
                current_article['context'].get('title_num'),
                current_article['context'].get('chapter'),
                current_article['context'].get('section_num'),
                current_article['context'].get('section_label'),
                current_article['num']
            ))
             updated_count += 1

             
        conn.commit()
        print(f"Successfully ingrained {updated_count} articles with structure.")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    ingest_rpc()
