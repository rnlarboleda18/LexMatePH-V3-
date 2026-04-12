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
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def parse_roc_file(filepath, book_label):
    """
    Parses an ROC Markdown file and returns a list of dictionaries.
    Each dictionary represents a Section, statefully preserving intermediate headers and paragraphs.
    """
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sections = []
    current_rule = None
    current_rule_title = None
    
    active_section = None
    pending_headers = []
    pending_rule_headers = [] # <--- Headers before the Rule line
    
    # Regexes
    rule_pattern = re.compile(r'^###\s+RULE\s+(\d+)(.*)', re.IGNORECASE)
    section_pattern = re.compile(r'^Section\s+(\d+)\.(.*)', re.IGNORECASE)
    
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

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if not line_stripped:
            if active_section:
                active_section['content_lines'].append("")
            continue

        # 1. Match Rule
        rule_match = rule_pattern.match(line_stripped)
        if rule_match:
            flush_section()
            current_rule = rule_match.group(1).strip()
            title_part = rule_match.group(2).strip()
            current_rule_title = title_part if title_part else ""
            
            # Subheaders BUFFERED BEFORE THE RULE become pending_rule_headers
            pending_rule_headers = list(pending_headers)
            pending_headers = [] # Reset for headers AFTER the rule
            continue

        # 2. Match Section
        sec_match = section_pattern.match(line_stripped)
        if sec_match:
            flush_section()
            sec_num = sec_match.group(1).strip()
            rest = sec_match.group(2).strip()
            
            # Split by title separator:
            # 1. Primary check on true dashes (Em-dash, En-dash) which do not require bounding spaces
            sep_match = re.search(r'^(.*?)[–—][\s\*]*(.*)', rest)
            
            if not sep_match:
                # 2. Fallback check for standard hyphens '-' which require spaces to not break compound words
                sep_match = re.search(r'^(.*?)\s+[-][\s\*]*(.*)', rest)
                if not sep_match:
                    sep_match = re.search(r'^(.*?)\s*[-][\s\*]+(.*)', rest)
            
            if sep_match:
                sec_title = sep_match.group(1).strip().replace('*', '')
                content = sep_match.group(2).strip()
            else:
                # Fallback: full rest is considered the title
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
                'book_label': book_label
            }
            pending_headers = [] # Reset after consuming
            continue

        # 3. Match Floating Sub-headers (Check BEFORE active_section to avoid swallowing)
        is_subheader = False
        if subheader_pattern1.match(line_stripped):
             is_subheader = True
        elif subheader_pattern2.match(line_stripped) and not line_stripped.startswith('### RULE'):
             is_subheader = True

        if is_subheader:
             flush_section() 
             clean_h = re.sub(r'^#+\s+', '', line_stripped).strip() # STRIP HASHES
             
             # FILTER OUT GARBAGE HEADERS
             clean_upper = clean_h.upper()
             if "REVISED RULES OF CRIMINAL PROCEDURE" in clean_upper or "2019 AMENDMENTS TO THE 1989 REVISED RULES ON EVIDENCE" in clean_upper:
                  continue
                  
             pending_headers.append(clean_h)
             continue

        if list_header_pattern.match(line_stripped) and len(line_stripped) < 40:
             flush_section() 
             pending_headers.append(line_stripped) # Already clean
             continue

        # 4. Append to active section content if inside section body
        if active_section:
             # Merge hanging broken citations: Lift 'Sec.' items to previous continuous line
             if line_stripped.startswith('Sec.') and active_section['content_lines']:
                  while active_section['content_lines'] and active_section['content_lines'][-1] == "":
                       active_section['content_lines'].pop()
                  # Add a space before appending to join cleanly without crowding
                  if active_section['content_lines']:
                       active_section['content_lines'][-1] += " "
             
             active_section['content_lines'].append(line_stripped)

    # Flush last section at end of file
    flush_section()
    return sections

def ingest_roc():
    files = [
        ('LexCode/Codals/md/ROC/1. ROC Civil Procedure as amended 2019.md', 'Civil Procedure'),
        ('LexCode/Codals/md/ROC/2. ROC Special Proceeding.md', 'Special Proceeding'),
        ('LexCode/Codals/md/ROC/3. ROC Criminal Procedure_cleaned.md', 'Criminal Procedure'),
        ('LexCode/Codals/md/ROC/4. ROC Evidence as amended 2019.md', 'Evidence')
    ]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Get Code ID for ROC
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'ROC'")
        row = cur.fetchone()
        
        if row:
            code_id = row[0]
            print(f"Found existing ROC Code ID: {code_id}")
        else:
            print("ROC Code entry not found. Creating...")
            cur.execute("""
                INSERT INTO legal_codes (full_name, short_name, description)
                VALUES ('Rules of Court', 'ROC', 'The Rules of Court of the Philippines')
                RETURNING code_id;
            """)
            code_id = cur.fetchone()[0]
            print(f"Created new ROC Code ID: {code_id}")

        # 2. Clear existing entries for re-run safety
        cur.execute("DELETE FROM article_versions WHERE code_id = %s", (code_id,))
        cur.execute("DELETE FROM roc_codal") # Full table clear for now, or filter by book if safer.
        print("Cleared existing ROC entries.")

        all_sections = []
        for file_idx, (filepath, label) in enumerate(files, start=1):
            print(f"Parsing {filepath}...")
            sections = parse_roc_file(filepath, label)
            print(f"Found {len(sections)} sections in {label}")
            for sec in sections:
                sec['book_num'] = file_idx # Add book number
            all_sections.extend(sections)

        print(f"Total sections found: {len(all_sections)}")

        # 3. Batch Insert into roc_codal
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
            sec_label = sec.get('section_label') # <--- Retrieve floating header separator

            # Article Number for versions and streaming
            article_num = f"Rule {rule}, Section {sec_num}"
            article_title = f"{rule_title} - {sec_title}" if rule_title and sec_title else sec_title or rule_title
            
            sec_label_before = sec.get('pending_rule_headers')

            # Combine
            base_title = f"Rule {rule} - {rule_title}" if rule_title else f"Rule {rule}"
            title_label = f"{sec_label_before}\n{base_title}" if sec_label_before else base_title

            # Prepare for roc_codal
            roc_args.append((
                book,                       # book_label 
                article_num,                # article_num (Compound)
                sec_title,                  # article_title (Section Title)
                content,                    # content_md
                title_label,                # title_label (Multi-line Rule Label)
                int(sec_num) if sec_num.isdigit() else None,  # section_num
                book_num,                   # book (Integer)
                sec_label                   # section_label
            ))

            # Prepare for article_versions
            ver_args.append((
                code_id,
                article_num,
                f"### {article_num}\n\n{content}", # include header for stream
                '2019-12-01', # Approx date for amendments
                None,
                'ROC'
            ))

        # Insert into roc_codal
        if roc_args:
             query = """
                INSERT INTO roc_codal 
                (book_label, article_num, article_title, content_md, title_label, section_num, book, section_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
             execute_batch(cur, query, roc_args)
             print(f"Inserted {len(roc_args)} into roc_codal")

        # Insert into article_versions
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
    ingest_roc()
