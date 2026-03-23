"""
Ingest Family Code from FC_structured.md into fc_codal table.
Maps: TITLE I MARRIAGE -> article_label='TITLE I', article_title='MARRIAGE'
      Chapter 1. Req... -> section_label='Chapter 1. Req...'
      Art. 1. ...      -> article_num='I-1', content_md=full text
"""
import re
import psycopg2
import os
import uuid

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"
BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
MD_FILE  = os.path.join(BASE_DIR, "CodexPhil", "Codals", "md", "FC_structured.md")
CODE     = "FC"
BOOK_CODE = "FAMILY CODE"

print(f"Reading {MD_FILE}...")
with open(MD_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

conn = psycopg2.connect(DB_CONNECTION)
cur  = conn.cursor()

# Clear existing FC rows so we don't double-insert
cur.execute("DELETE FROM fc_codal WHERE book_code = %s", (CODE,))
print(f"Cleared existing rows for {CODE}")

# Check if book_code column exists, add it if not
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='fc_codal' AND column_name='book_code'
""")
if not cur.fetchone():
    cur.execute("ALTER TABLE fc_codal ADD COLUMN book_code text")
    print("Added book_code column")

# Check group_header column
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='fc_codal' AND column_name='group_header'
""")
if not cur.fetchone():
    cur.execute("ALTER TABLE fc_codal ADD COLUMN group_header text")
    print("Added group_header column")

conn.commit()

# --- PARSE THE MARKDOWN ---
pat_title   = re.compile(r'^##\s+(TITLE\s+[IVXLCDM]+)\s+(.*)', re.IGNORECASE)
pat_chapter = re.compile(r'^###\s+(Chapter\s+\d+\..*)', re.IGNORECASE)
pat_section = re.compile(r'^####\s+(Section\s+\d+\..*)', re.IGNORECASE)
pat_art     = re.compile(r'^#####\s+(Art(?:icle)?\.\s+(\d+)\.)(.*)', re.IGNORECASE)

ctx = {
    'title_label': None,    # e.g. 'TITLE I'
    'title_name':  None,    # e.g. 'MARRIAGE'
    'chapter':     None,    # e.g. 'Chapter 1. Requisites of Marriage'
    'section_hdr': None,    # e.g. 'Section 1. General Provisions'
    'art_num':     None,    # e.g. '1'
    'art_full_num': None,   # e.g. 'I-1'
    'body':        [],
}

inserted_count = 0

def get_list_order():
    cur.execute("SELECT COALESCE(MAX(list_order), 0) + 1 FROM fc_codal")
    return cur.fetchone()[0]

def flush_article():
    global inserted_count
    if not ctx['art_num']:
        return
    body = "\n".join(ctx['body']).strip()
    
    # Auto-format inline enumerations into markdown lists
    body = re.sub(r' (?=\(\d+\)\s)', '\n\n', body)
    body = re.sub(r' (?=\([a-z]\)\s)', '\n\n', body)
    body = re.sub(r'\n{3,}', '\n\n', body)
    
    if not body:
        ctx['body'] = []
        return

    article_num    = ctx['art_full_num']
    article_title  = ctx['title_name'] or ''
    article_label  = ctx['title_label'] or ''
    section_label  = ctx['chapter'] or ''
    group_header   = f"FAMILY CODE\n{article_label} {article_title}".strip()
    list_order     = get_list_order()
    new_id         = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO fc_codal
            (id, article_num, article_label, article_title, section_label,
             content_md, list_order, book_code, group_header, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    """, (new_id, article_num, article_label, article_title, section_label,
          body, list_order, CODE, group_header))

    inserted_count += 1
    ctx['body'] = []

for line in lines:
    stripped = line.strip()

    # TITLE II LEGAL SEPARATION
    m = pat_title.match(stripped)
    if m:
        flush_article()
        ctx['title_label']  = m.group(1).upper()
        ctx['title_name']   = m.group(2).strip()
        ctx['chapter']      = None
        ctx['section_hdr']  = None
        ctx['art_num']      = None
        ctx['art_full_num'] = None
        continue

    # Chapter 1. Requisites of Marriage
    m = pat_chapter.match(stripped)
    if m:
        flush_article()
        ctx['chapter']      = m.group(1).strip()
        ctx['section_hdr']  = None
        ctx['art_num']      = None
        ctx['art_full_num'] = None
        continue

    # Section 1. General Provisions  (sub-chapter)
    m = pat_section.match(stripped)
    if m:
        flush_article()
        ctx['section_hdr']  = m.group(1).strip()
        ctx['art_num']      = None
        ctx['art_full_num'] = None
        continue

    # Art. 1. Content...
    m = pat_art.match(stripped)
    if m:
        flush_article()
        art_num = m.group(2)
        ctx['art_num']      = art_num
        # Short title prefix: extract roman numeral from title_label
        roman = 'FC'
        if ctx['title_label']:
            rm = re.search(r'TITLE\s+([IVXLCDM]+)', ctx['title_label'], re.IGNORECASE)
            if rm:
                roman = rm.group(1).upper()
        ctx['art_full_num'] = f"FC-{roman}-{art_num}"
        # Section label: now use Chapter if set
        ctx['chapter'] = ctx['chapter'] or ctx['section_hdr']
        # Body starts with rest of article line
        rest = m.group(3).strip()
        if rest:
            ctx['body'].append(rest)
        continue

    # Body text
    if ctx['art_num']:
        ctx['body'].append(stripped)

flush_article()
conn.commit()
print(f"Ingested {inserted_count} articles into fc_codal (book_code={CODE!r})")
conn.close()
