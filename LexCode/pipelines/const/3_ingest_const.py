"""
Ingest Constitution from Structured Markdown to DB (const_codal) - V2 (Cleaned Headers)
"""
import re
import psycopg2
import os

# Configuration
DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"
BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
MD_FILE_PATH = os.path.join(BASE_DIR, "LexCode", "Codals", "md", "1987_Philippine_Constitution_Structured.md")

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION)

def ingest_const():
    print(f"Reading {MD_FILE_PATH}...")
    with open(MD_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    conn = get_db_connection()
    cur = conn.cursor()

    # Step 1: Wipe existing Constitution records first
    cur.execute("DROP TABLE IF EXISTS consti_codal;") # Wiping just the Constitution table
    cur.execute("""
        CREATE TABLE consti_codal (
            id SERIAL PRIMARY KEY,
            article_num TEXT,
            article_label TEXT,
            article_title TEXT,
            section_num TEXT,
            section_label TEXT,
            group_header TEXT,
            content_md TEXT,
            book_code TEXT DEFAULT 'CONST',
            list_order INTEGER
        );
    """)
    print("Dropped and recreated 'consti_codal' table.")

    current_context = {
        'article_lbl': None,
        'article_title': None,
        'group_header': None
    }
    
    current_section = {
        'num': None,
        'label': None,
        'body': []
    }
    
    inserted_count = 0
    
    pat_article = re.compile(r'^##\s+(ARTICLE\s+[IVXLCDM]+)\s+(.*)', re.IGNORECASE)
    pat_article_simple = re.compile(r'^##\s+(ARTICLE\s+[IVXLCDM]+)$', re.IGNORECASE)
    pat_preamble = re.compile(r'^##\s+PREAMBLE', re.IGNORECASE)
    pat_section = re.compile(r'^###\s+(Section\s+(\d+)\.)(.*)', re.IGNORECASE)
    pat_group = re.compile(r'^####\s+(.*)', re.IGNORECASE)
    
    def flush_section():
        nonlocal inserted_count
        body_text = "".join(current_section['body']).strip()
        # ONLY insert if we have a section label AND some actual body content
        if current_section['label'] and body_text:
            art_roman = "PRE"
            if current_context['article_lbl']:
                match = re.search(r'ARTICLE\s+([IVXLCDM]+)', current_context['article_lbl'], re.IGNORECASE)
                if match:
                    art_roman = match.group(1).upper()
            
            sec_num = current_section['num'] if current_section['num'] else '0'
            article_id = f"{art_roman}-{sec_num}"
            
            if current_context['article_lbl'] == "PREAMBLE":
                article_id = "PREAMBLE"
                art_roman = "PREAMBLE"
                sec_num = "0"
            
            cur.execute("""
                INSERT INTO consti_codal (article_num, article_title, content_md, article_label, section_num, section_label, group_header, book_code, list_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                article_id,
                current_context['article_title'],
                body_text,
                current_context['article_lbl'],
                sec_num,
                current_section['label'],
                current_context['group_header'],
                'CONST',
                inserted_count + 1
            ))
            inserted_count += 1
            
        current_section['body'] = []
        # DO NOT clear label/num here, as we might be continuing same section after a group header?
        # Actually, in PH Const, Sections don't span across Group Headers.
        # But let's be safe. If we found a group header, it should have flushed the previous section.
        current_section['label'] = None
        current_section['num'] = None

    for line in lines:
        # Preamble
        if pat_preamble.match(line):
            flush_section()
            current_context['article_lbl'] = "PREAMBLE"
            current_context['article_title'] = "PREAMBLE"
            current_context['group_header'] = None
            current_section['label'] = "PREAMBLE"
            current_section['num'] = "0"
            continue
            
        # Article Header
        match = pat_article.match(line)
        if match:
            flush_section()
            current_context['article_lbl'] = match.group(1).upper()
            current_context['article_title'] = match.group(2).strip()
            current_context['group_header'] = None
            # Note: We don't set current_section['label'] to Article here anymore 
            # to avoid inserting empty Article rows.
            continue
            
        match_simple = pat_article_simple.match(line)
        if match_simple:
            flush_section()
            current_context['article_lbl'] = match_simple.group(1).upper()
            current_context['article_title'] = None
            current_context['group_header'] = None
            continue

        # Group Header
        match_group = pat_group.match(line)
        if match_group:
            flush_section() 
            current_context['group_header'] = match_group.group(1).strip()
            continue

        # Section Header
        match = pat_section.match(line)
        if match:
            flush_section()
            current_section['label'] = match.group(1).strip()
            current_section['num'] = match.group(2)
            if match.group(3).strip():
                 current_section['body'].append(match.group(3).strip() + "\n")
            continue
            
        # Body
        if current_section['label'] or current_context['article_lbl']:
            # If we have an article but no section yet, treat as "Section 0" or just label it by the Article
            if not current_section['label']:
                current_section['label'] = current_context['article_lbl']
                current_section['num'] = "0"
            current_section['body'].append(line)
        
    flush_section() 
    
    conn.commit()
    print(f"Ingested {inserted_count} clean sections into consti_codal.")
    conn.close()

if __name__ == "__main__":
    ingest_const()
