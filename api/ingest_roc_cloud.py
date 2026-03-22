import psycopg2
import json
import re
import os
from psycopg2.extras import execute_batch

# Cloud connection string
CLOUD_DB = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def parse_roc_combined(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sections = []
    current_rule = None
    current_rule_title = None
    current_book_label = "Rules of Court"
    current_book_num = 0
    
    active_section = None
    pending_group_headers = [] # Stack for groups
    
    # Regexes
    rule_pattern = re.compile(r'^###\s+RULE\s+(\d+)(.*)', re.IGNORECASE)
    section_pattern = re.compile(r'^Section\s+(\d+)\.(.*)', re.IGNORECASE)
    part_pattern = re.compile(r'^PART\s+([IVX]+)\s+(.*)', re.IGNORECASE)
    
    # Sub-headers (floating text that looks like a header)
    subheader_pattern = re.compile(r'^[A-Z][A-Z\s,]+$|^#\s+[^#]+') # All caps lines or H1

    def flush_section():
        nonlocal active_section
        if active_section:
            content_lines = active_section.get('content_lines', [])
            
            # Calculate min_indent for normalization
            non_empty_lines = [l for l in content_lines if l.strip()]
            min_indent = 0
            if non_empty_lines:
                min_indent = min(len(l) - len(l.lstrip()) for l in non_empty_lines)

            processed_lines = []
            for line in content_lines:
                if line.strip():
                    stripped = line.lstrip()
                    spaces_count = len(line) - len(stripped)
                    # Normalize baseline
                    adjusted_indent = max(0, spaces_count - min_indent)
                    
                    # Protect leading spaces with invisible Zero Width Non-Joiner and non-breaking spaces
                    indent = "\u200C" + ("\u00A0" * adjusted_indent)
                    processed_lines.append(indent + stripped)
                else:
                    processed_lines.append("")
            
            content_md = "\n".join(processed_lines).strip()
            
            # Extract source_ref like (1a), (n), (R143a) at the very end
            source_match = re.search(r'\s*\(([^)]+)\)\.?$', content_md)
            if source_match:
                active_section['source_ref'] = f"({source_match.group(1)})"
                # Strip it from content
                content_md = content_md[:source_match.start()].strip()
            
            # Basic cleanup of bracket annotations if any
            content_md = re.sub(r'\[\((.+?)\)\]', r'(\1)', content_md)
            content_md = re.sub(r'\[([a-zA-Z0-9;,. _\-]+)\]', r'\1', content_md)
            
            active_section['section_content'] = content_md
            del active_section['content_lines']
            sections.append(active_section)
            active_section = None

    for line in lines:
        line_raw = line.rstrip('\n')
        line_stripped = line_raw.strip()
        
        if not line_stripped:
            if active_section:
                active_section['content_lines'].append("") # Preserve empty lines
            continue

        # 0. Book level (PART I, etc)
        part_match = part_pattern.match(line_stripped)
        if part_match:
            flush_section()
            roman = part_match.group(1).upper()
            label = part_match.group(2).strip()
            current_book_label = label.title()
            roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}
            current_book_num = roman_map.get(roman, 0)
            pending_group_headers = []
            continue

        # 1. Rule level (may be inside <p> tag)
        temp_line = re.sub(r'<[^>]+>', ' ', line_stripped).strip()
        rule_match = rule_pattern.search(temp_line)
        if rule_match:
            flush_section()
            current_rule = rule_match.group(1).strip()
            title_part = rule_match.group(2).strip()
            current_rule_title = title_part if title_part else "Provisions"
            
            if '<br>' in line_stripped.lower():
                parts = re.split(r'<br>', line_stripped, flags=re.IGNORECASE)
                if len(parts) > 1:
                     current_rule_title = re.sub(r'<[^>]+>', '', parts[1]).strip()
            continue

        # 2. Section level
        sec_match = section_pattern.match(line_stripped)
        if sec_match:
            flush_section()
            sec_num = sec_match.group(1).strip()
            rest = sec_match.group(2).strip()
            
            # Section 1. *Title*. — Content
            title_match = re.search(r'^\s*\*?(.*?)\*?[\.\s]*[—–]\s*(.*)', rest)
            if title_match:
                sec_title = title_match.group(1).strip()
                content = title_match.group(2).strip()
            else:
                sec_title = rest
                content = ""

            group_1 = pending_group_headers[0] if len(pending_group_headers) > 0 else None
            group_2 = pending_group_headers[1] if len(pending_group_headers) > 1 else None

            active_section = {
                'part_num': current_book_num,
                'part_title': current_book_label,
                'rule_num': current_rule,
                'rule_title': current_rule_title,
                'section_num': sec_num,
                'section_title': sec_title,
                'content_lines': [content] if content else [],
                'group_1_title': group_1,
                'group_2_title': group_2,
                'source_ref': None
            }
            # Note: We don't clear pending_group_headers here because they might apply to multiple rules/sections
            continue

        # 3. Intermediate headers (H1-H5 or All-Caps)
        if (line_stripped.startswith('#') or (line_stripped.isupper() and len(line_stripped) > 5)) and not line_stripped.startswith('Section'):
             # Determine level
             level = 0
             header_text = line_stripped
             if line_stripped.startswith('#'):
                 match = re.match(r'^(#+)\s+(.*)', line_stripped)
                 if match:
                     level = len(match.group(1))
                     header_text = match.group(2).strip()
             
             # Map levels to pending_group_headers
             # Level 1 or 2 (or all-caps) -> Position 0
             # Level 4 -> Position 0 (resets 1)
             # Level 5 -> Position 1
             if level == 4 or (level == 0 and line_stripped.isupper()):
                  pending_group_headers = [header_text, None]
             elif level == 5:
                  if len(pending_group_headers) < 1:
                      pending_group_headers = [None, header_text]
                  else:
                      if len(pending_group_headers) == 1:
                          pending_group_headers.append(header_text)
                      else:
                          pending_group_headers[1] = header_text
             elif level > 0 and level < 4:
                  # Generic H1-H3 headers (like PART or RULE handled above, but just in case)
                  pending_group_headers = [header_text, None]
             continue

        # 4. Content
        if active_section:
            # Preserve indentation for content lines
            active_section['content_lines'].append(line_raw)

    flush_section()
    return sections

def ingest_to_cloud():
    filepath = 'CodexPhil/Codals/md/ROC/ROC_Combined.md'
    if not os.path.exists(filepath):
         filepath = 'CodexPhil/Codals/md/clean/ROC/ROC_Combined.md'

    print(f"Connecting to CLOUD DB...")
    conn = psycopg2.connect(CLOUD_DB)
    cur = conn.cursor()

    try:
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'ROC'")
        row = cur.fetchone()
        code_id = row[0]

        print("Clearing existing cloud ROC data...")
        cur.execute("DELETE FROM roc_codal")
        cur.execute("DELETE FROM article_versions WHERE code_id = %s", (code_id,))

        print(f"Parsing {filepath}...")
        results = parse_roc_combined(filepath)
        print(f"Parsed {len(results)} sections.")

        roc_inserts = []
        ver_inserts = []

        for res in results:
            rule = res['rule_num']
            rule_title = res['rule_title']
            sec_num = res['section_num']
            sec_title = res['section_title']
            content = res['section_content']
            part_title = res['part_title']
            part_num = res['part_num']
            g1 = res['group_1_title']
            g2 = res['group_2_title']
            sref = res['source_ref']

            article_num = f"Rule {rule}, Section {sec_num}"
            rule_title_full = f"RULE {rule} {rule_title}"

            roc_inserts.append((
                part_num,            # part_num (int)
                int(rule) if rule and rule.isdigit() else 0, # rule_num
                rule_title_full,      # rule_title_full
                article_num,         # rule_section_label
                sec_title,           # section_title
                content,             # section_content
                part_title,          # part_title
                int(sec_num) if sec_num.isdigit() else 0, # section_num
                g1,                  # group_1_title
                g2,                  # group_2_title
                sref                 # source_ref
            ))

            ver_inserts.append((
                code_id,
                article_num,
                f"### {article_num}\n\n{content}",
                '2019-12-01',
                'ROC'
            ))

        if roc_inserts:
            query = """
                INSERT INTO roc_codal (part_num, rule_num, rule_title_full, rule_section_label, section_title, section_content, part_title, section_num, group_1_title, group_2_title, source_ref)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_batch(cur, query, roc_inserts)
            print(f"Inserted {len(roc_inserts)} rows into cloud roc_codal.")

        if ver_inserts:
            query = """
                INSERT INTO article_versions (code_id, article_number, content, valid_from, amendment_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            execute_batch(cur, query, ver_inserts)
            print(f"Inserted {len(ver_inserts)} rows into cloud article_versions.")

        conn.commit()
        print("Done.")

    except Exception as e:
        print(f"Error during ingestion: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_to_cloud()
