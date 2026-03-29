"""
5_reingest_const_clean.py
Re-ingests the 1987 Philippine Constitution from the source MD into consti_codal.

HIERARCHY RULES (as confirmed from source MD):
  1. PREAMBLE         → article_num='0', section_num='0'
  2. ARTICLE X        → article label + article title (next non-blank line after ARTICLE)
  3. Subheader        → any short standalone line (surrounded by blanks) appearing between
                        the article title and first SECTION, or between two SECTIONs.
                        Examples: "Principles", "State Policies", "A. Common Provisions"
                        Stored in group_header column.
  4. SECTION N.       → article_num = '{ROMAN}-{N}' for normal articles
                        article_num = '{ROMAN}-{SubLetter}-{N}' for Art. IX sub-articles
  5. Article I        → has body but no SECTION markers → article_num='I-0'

ENCODING:
  - Art. II Sec 5    → article_num = 'II-5'
  - Art. IX-A Sec 1  → article_num = 'IX-A-1'
  - Art. IX-B Sec 3  → article_num = 'IX-B-3'
  - Preamble         → article_num = '0'
  - Art. I body      → article_num = 'I-0'
"""

import re
import psycopg2

DB_URI = "postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"
MD_PATH = r"CodexPhil/Codals/md/1987_Philippine_Constitution.md"

ARTICLE_PAT  = re.compile(r'^ARTICLE\s+([IVXLCDM]+(?:-[A-Z]+)?)\s*$')
SECTION_PAT  = re.compile(r'^SECTION\s+(\d+)\.')
PREAMBLE_PAT = re.compile(r'^PREAMBLE\s*$')
SUBART_PAT   = re.compile(r'^([A-D])\.\s+(.+)$')   # "A. Common Provisions"

def is_blank(s):
    return not s.strip()

def is_subheader_candidate(stripped, prev_was_blank, next_is_blank):
    """
    A line is a subheader if it is:
    - Non-blank
    - Surrounded by blank lines
    - Short (< 10 words)
    - Does NOT start with SECTION/ARTICLE/PREAMBLE
    - Does NOT start lowercase
    - Does NOT end with a sentence-ending character
    - Is NOT a quoted string starting with "I do..."
    - NOT just a number or markdown escape
    """
    if not stripped:
        return False
    if not prev_was_blank or not next_is_blank:
        return False
    if len(stripped.split()) > 10:
        return False
    if SECTION_PAT.match(stripped):
        return False
    if ARTICLE_PAT.match(stripped):
        return False
    if PREAMBLE_PAT.match(stripped):
        return False
    if stripped[0].islower():
        return False
    if stripped[-1] in '.,;:':
        return False
    if stripped.startswith('\\'):
        return False
    if stripped.startswith('"'):
        return False
    return True

def build_article_num(roman, sub_letter, section_num):
    if sub_letter:
        return f"{roman}-{sub_letter}-{section_num}"
    return f"{roman}-{section_num}"

def run():
    print(f"Reading {MD_PATH}...")
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()

    lines = [l.rstrip('\r\n') for l in raw_lines]
    N = len(lines)

    # ---- Parse structure into tokens ----
    # Each token: {'type': ARTICLE|ARTICLE_TITLE|SUBHEADER|SECTION|BODY|PREAMBLE, ...}
    tokens = []
    i = 0

    while i < N:
        s = lines[i].strip()

        if is_blank(lines[i]):
            i += 1
            continue

        # PREAMBLE
        if PREAMBLE_PAT.match(s):
            tokens.append({'type': 'PREAMBLE', 'line': i+1})
            i += 1
            continue

        # ARTICLE
        am = ARTICLE_PAT.match(s)
        if am:
            tokens.append({'type': 'ARTICLE', 'roman': am.group(1), 'line': i+1})
            i += 1
            continue

        # SECTION
        sm = SECTION_PAT.match(s)
        if sm:
            tokens.append({'type': 'SECTION', 'num': sm.group(1), 'text': lines[i], 'line': i+1})
            i += 1
            continue

        # Check for subheader: surrounded by blanks
        prev_blank = (i == 0) or is_blank(lines[i-1])
        next_blank = (i == N-1) or is_blank(lines[i+1])

        if is_subheader_candidate(s, prev_blank, next_blank):
            # Is it a sub-article (A./B./C./D.) or plain subheader?
            sabm = SUBART_PAT.match(s)
            if sabm:
                tokens.append({'type': 'SUB_ARTICLE', 'letter': sabm.group(1),
                                'label': s, 'line': i+1})
            else:
                tokens.append({'type': 'SUBHEADER', 'label': s, 'line': i+1})
            i += 1
            continue

        # Body text
        tokens.append({'type': 'BODY', 'text': lines[i], 'line': i+1})
        i += 1

    print(f"Parsed {len(tokens)} tokens.")

    # ---- Convert tokens to DB rows ----
    rows = []
    list_order = 0

    current_article = None       # roman numeral string e.g. 'II'
    current_title = None         # article title string
    current_sub_letter = None    # 'A', 'B', 'C', 'D' or None
    current_sub_label = None     # 'A. Common Provisions' or None (plain for II)
    current_group_header = None  # current group_header value
    current_section_num = None
    current_body_lines = []
    in_preamble = False
    article_i_body = []  # Special: Art I has no SECTION

    def flush():
        nonlocal list_order
        body = '\n'.join(current_body_lines).strip()

        if in_preamble:
            list_order += 1
            rows.append({
                'article_num': '0',
                'article_label': 'PREAMBLE',
                'article_title': 'PREAMBLE',
                'section_num': '0',
                'section_label': 'PREAMBLE',
                'group_header': None,
                'title_label': 'PREAMBLE',
                'content_md': body,
                'list_order': list_order
            })
            return

        if current_article and current_section_num is not None:
            art_num = build_article_num(current_article, current_sub_letter, current_section_num)
            list_order += 1
            rows.append({
                'article_num': art_num,
                'article_label': f'ARTICLE {current_article}',
                'article_title': current_title,
                'section_num': current_section_num,
                'section_label': f'SECTION {current_section_num}.',
                'group_header': current_group_header,
                'title_label': current_title,
                'content_md': body,
                'list_order': list_order
            })

    is_preamble_ctx = False
    is_after_article_title = False
    article_i_in_progress = False

    for idx, tok in enumerate(tokens):
        tt = tok['type']

        if tt == 'PREAMBLE':
            flush()
            is_preamble_ctx = True
            current_article = None
            current_title = None
            current_sub_letter = None
            current_sub_label = None
            current_group_header = None
            current_section_num = None
            current_body_lines = []
            in_preamble = True
            is_after_article_title = False

        elif tt == 'ARTICLE':
            flush()
            # Flush any Article I body (no sections)
            if article_i_in_progress and current_body_lines:
                body = '\n'.join(current_body_lines).strip()
                list_order += 1
                rows.append({
                    'article_num': f'{current_article}-0',
                    'article_label': f'ARTICLE {current_article}',
                    'article_title': current_title,
                    'section_num': '0',
                    'section_label': f'ARTICLE {current_article}.',
                    'group_header': None,
                    'title_label': current_title,
                    'content_md': body,
                    'list_order': list_order
                })
            current_article = tok['roman']
            current_title = None
            current_sub_letter = None
            current_sub_label = None
            current_group_header = None
            current_section_num = None
            current_body_lines = []
            in_preamble = False
            is_after_article_title = False
            # The immediately following non-blank token should be the article title
            # We'll handle it via the next SUBHEADER/BODY token
            # Set a flag to consume the next BODY/SUBHEADER as the title
            is_after_article_title = True
            article_i_in_progress = (tok['roman'] == 'I')

        elif tt == 'SUB_ARTICLE':
            # End previous section
            flush()
            current_section_num = None
            current_body_lines = []
            current_sub_letter = tok['letter']
            current_sub_label = tok['label']
            current_group_header = tok['label']

        elif tt == 'SUBHEADER':
            # Plain subheader (e.g. "Principles", "State Policies")
            # Check if it's actually the article title (first subheader-like after ARTICLE)
            if is_after_article_title and current_title is None:
                # This is the article title
                current_title = tok['label']
                is_after_article_title = False
                print(f"  Article {current_article} title: '{current_title}'")
            else:
                # It's a real group subheader between sections
                flush()
                current_section_num = None
                current_body_lines = []
                current_group_header = tok['label']
                print(f"  Article {current_article} subheader: '{tok['label']}'")

        elif tt == 'BODY':
            # Check if we need this as the article title
            if is_after_article_title and current_title is None:
                current_title = tok['text'].strip()
                is_after_article_title = False
                print(f"  Article {current_article} title: '{current_title}'")
            elif in_preamble or current_section_num is not None or article_i_in_progress:
                current_body_lines.append(tok['text'])

        elif tt == 'SECTION':
            flush()
            current_section_num = tok['num']
            current_body_lines = [tok['text']]
            in_preamble = False
            article_i_in_progress = False

    # Flush last
    flush()

    print(f"\nTotal rows to insert: {len(rows)}")
    print("\nSubheaders found:")
    for r in rows:
        if r['group_header']:
            print(f"  article_num={r['article_num']:12} group_header='{r['group_header']}'")
            break  # Just show first occurrence of each group_header
    seen_headers = set()
    for r in rows:
        gh = r['group_header']
        if gh and gh not in seen_headers:
            seen_headers.add(gh)
            print(f"  group_header='{gh}'")

    # ---- Write to DB ----
    print("\nConnecting to database...")
    conn = psycopg2.connect(DB_URI)
    cur = conn.cursor()

    print("TRUNCATING consti_codal...")
    cur.execute("TRUNCATE TABLE consti_codal;")

    # Check if group_header column exists
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'consti_codal' AND column_name = 'group_header'
    """)
    has_group_header = cur.fetchone() is not None

    if not has_group_header:
        print("Adding group_header column...")
        cur.execute("ALTER TABLE consti_codal ADD COLUMN group_header TEXT;")

    # Check if title_label column exists
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'consti_codal' AND column_name = 'title_label'
    """)
    has_title_label = cur.fetchone() is not None

    if not has_title_label:
        print("Adding title_label column...")
        cur.execute("ALTER TABLE consti_codal ADD COLUMN title_label TEXT;")

    print("Inserting rows...")
    for r in rows:
        cur.execute("""
            INSERT INTO consti_codal
              (article_num, article_label, article_title, section_num, section_label,
               group_header, title_label, content_md, list_order, book_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'CONST')
        """, (
            r['article_num'],
            r['article_label'],
            r['article_title'],
            r['section_num'],
            r['section_label'],
            r['group_header'],
            r['title_label'],
            r['content_md'],
            r['list_order']
        ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✓ Ingested {len(rows)} rows into consti_codal.")

if __name__ == '__main__':
    run()
