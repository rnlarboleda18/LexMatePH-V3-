import psycopg2
import json
import re
import os
from psycopg2.extras import execute_batch

def get_db_connection():
    try:
        with open('api/local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def parse_roc_combined(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sections = []
    current_rule = None
    current_rule_title = None
    current_book = "Rules of Court"
    current_book_num = 0
    
    active_section = None
    pending_headers = []
    pending_rule_headers = [] 
    
    # Regexes
    rule_pattern = re.compile(r'^###\s+RULE\s+(\d+)(.*)', re.IGNORECASE)
    section_pattern = re.compile(r'^Section\s+(\d+)\.(.*)', re.IGNORECASE)
    part_pattern = re.compile(r'^PART\s+([IVX]+)\s+(.*)', re.IGNORECASE)
    
    # Sub-headers match
    subheader_pattern1 = re.compile(r'^##\s+(.*)') 
    subheader_pattern2 = re.compile(r'^###\s+(?!RULE)(.*)') 
    list_header_pattern = re.compile(r'^\d+\.\s+[A-Z][a-zA-Z\s,\[\]\(\)]+$') 

    def flush_section():
        nonlocal active_section
        if active_section:
            content_lines = active_section.get('content_lines', [])
            content_md = "\n".join(content_lines).strip()
            
            # 1. Strip [ (X) ] and [x] bracket annotations
            content_md = re.sub(r'\[\((.+?)\)\]', r'(\1)', content_md)
            content_md = re.sub(r'\[([a-zA-Z0-9;,. _\-]+)\]', r'\1', content_md)
            
            active_section['content_md'] = content_md
            del active_section['content_lines']
            sections.append(active_section)
            active_section = None

    for line in lines:
        line_stripped = line.strip()
        
        if not line_stripped:
            if active_section:
                active_section['content_lines'].append("")
            continue

        # 0. Match PART (Book change)
        part_match = part_pattern.match(line_stripped)
        if part_match:
            flush_section()
            roman = part_match.group(1).upper()
            label = part_match.group(2).strip()
            current_book = label.title()
            roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}
            current_book_num = roman_map.get(roman, 0)
            pending_rule_headers = []
            pending_headers = []
            continue

        # 1. Match Rule
        rule_match = rule_pattern.match(line_stripped)
        # Catch Rule line even inside centered <p> tags
        if not rule_match and '<p' in line_stripped and 'RULE' in line_stripped:
             tag_shorn = re.sub(r'<[^>]+>', '', line_stripped).strip()
             rule_match = rule_pattern.match(tag_shorn)

        if rule_match:
            flush_section()
            current_rule = rule_match.group(1).strip()
            title_part = rule_match.group(2).strip()
            current_rule_title = title_part if title_part else ""
            
            pending_rule_headers = list(pending_headers)
            pending_headers = [] 
            continue

        # 2. Match Section
        sec_match = section_pattern.match(line_stripped)
        if sec_match:
            flush_section()
            sec_num = sec_match.group(1).strip()
            rest = sec_match.group(2).strip()
            
            # Split by title separator:
            sep_match = re.search(r'^(.*?)[–—][\s\*]*(.*)', rest)
            
            if not sep_match:
                sep_match = re.search(r'^(.*?)\s+[-][\s\*]*(.*)', rest)
                if not sep_match:
                    sep_match = re.search(r'^(.*?)\s*[-][\s\*]+(.*)', rest)
            
            if sep_match:
                sec_title = sep_match.group(1).strip().replace('*', '')
                content = sep_match.group(2).strip()
            else:
                sec_title = rest.strip().replace('*', '')
                content = ""

            content_lines = [content] if content else []

            active_section = {
                'rule_num': current_rule,
                'rule_title': current_rule_title,
                'section_num': sec_num,
                'section_title': sec_title,
                'content_lines': content_lines,
                'section_label': "\n".join(pending_headers) if pending_headers else None,
                'pending_rule_headers': "\n".join(pending_rule_headers) if pending_rule_headers else None,
                'book_label': current_book,
                'book_num': current_book_num
            }
            pending_headers = [] 
            continue

        # 3. Match Floating Sub-headers
        is_subheader = False
        if subheader_pattern1.match(line_stripped):
             is_subheader = True
        elif subheader_pattern2.match(line_stripped) and 'RULE' not in line_stripped:
             is_subheader = True

        if is_subheader:
             flush_section() 
             clean_h = re.sub(r'^#+\s+', '', line_stripped).strip()
             clean_h = re.sub(r'<[^>]+>', '', clean_h).strip() # Strip HTML tags if any
             
             if "REVISED RULES OF" in clean_h.upper():
                  continue
                  
             pending_headers.append(clean_h)
             continue

        # 4. Append to active section content if inside section body
        if active_section:
             active_section['content_lines'].append(line_stripped)

    flush_section()
    return sections

def ingest_roc_combined():
    filepath = 'CodexPhil/Codals/md/clean/ROC/ROC_Combined.md'
    
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'ROC'")
        row = cur.fetchone()
        if row:
            code_id = row[0]
            print(f"Found existing ROC Code ID: {code_id}")
        else:
            cur.execute("""
                INSERT INTO legal_codes (full_name, short_name, description)
                VALUES ('Rules of Court', 'ROC', 'The Rules of Court of the Philippines')
                RETURNING code_id;
            """)
            code_id = cur.fetchone()[0]
            print(f"Created new ROC Code ID: {code_id}")

        cur.execute("DELETE FROM article_versions WHERE code_id = %s", (code_id,))
        cur.execute("DELETE FROM roc_codal")
        print("Cleared existing ROC entries.")

        print(f"Parsing {filepath}...")
        all_sections = parse_roc_combined(filepath)
        print(f"Total sections found: {len(all_sections)}")

        roc_args = []
        ver_args = []

        for sec in all_sections:
            rule = sec['rule_num']
            rule_title = sec['rule_title']
            sec_num = sec['section_num']
            sec_title = sec['section_title']
            content = sec['content_md']
            book = sec['book_label']
            book_num = sec['book_num']
            sec_label = sec.get('section_label') 
            sec_label_before = sec.get('pending_rule_headers')

            article_num = f"Rule {rule}, Section {sec_num}"
            article_title = f"{rule_title} - {sec_title}" if rule_title and sec_title else sec_title or rule_title
            
            base_rule_label = f"Rule {rule} - {rule_title}" if rule_title else f"Rule {rule}"
            title_label = f"{sec_label_before}\n{base_rule_label}" if sec_label_before else base_rule_label

            roc_args.append((
                book,                       # book_label 
                article_num,                # article_num (Compound)
                sec_title,                  # article_title (Section Title)
                content,                    # content_md
                title_label,                # title_label (Multi-line Rule Label)
                int(sec_num) if sec_num.isdigit() else 0, # section_num
                book_num,                   # book (Integer)
                sec_label                   # section_label
            ))

            ver_args.append((
                code_id,
                article_num,
                f"### {article_num}\n\n{content}",
                '2019-12-01',
                None,
                'ROC'
            ))

        if roc_args:
             query = """
                INSERT INTO roc_codal 
                (book_label, article_num, article_title, content_md, title_label, section_num, book, section_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
             execute_batch(cur, query, roc_args)
             print(f"Inserted {len(roc_args)} into roc_codal")

        if ver_args:
             query = """
                INSERT INTO article_versions 
                (code_id, article_number, content, valid_from, valid_to, amendment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
             execute_batch(cur, query, ver_args)
             print(f"Inserted {len(ver_args)} into article_versions")

        conn.commit()
        print("Ingestion complete.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_roc_combined()
