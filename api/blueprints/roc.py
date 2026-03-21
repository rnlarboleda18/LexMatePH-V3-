import logging
import json
import os
import azure.functions as func
import psycopg2
import re
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

roc_bp = func.Blueprint()

def clean_roman_rules(text):
    if not text: return text
    
    def roman_to_int(s):
        rom_val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        int_val = 0
        s = s.upper()
        try:
            for i in range(len(s)):
                if i > 0 and rom_val[s[i]] > rom_val[s[i - 1]]:
                    int_val += rom_val[s[i]] - 2 * rom_val[s[i - 1]]
                else:
                    int_val += rom_val[s[i]]
            return int_val
        except:
            return None
            
    def replace_match(m):
        val = roman_to_int(m.group(1))
        if val is not None:
            return f"{m.group(0).split(' ')[0]} {val}" # preserves "Rule" or "RULE"
        return m.group(0)

    # Match "Rule IV", "RULE IV", etc.
    return re.sub(r'(?i)\brule\s+([IVXLCDM]+)\b', replace_match, str(text))

@roc_bp.route(route="roc/book/{book_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_roc_by_book(req: func.HttpRequest) -> func.HttpResponse:
    book_num = req.route_params.get('book_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Sort by Rule number (rule_num) and then section_num
        cur.execute("""
            SELECT *, 
                   part_num AS book,
                   part_title AS book_label,
                   rule_num AS title_num,
                   rule_title_full AS title_label,
                   group_1_title AS chapter_label,
                   group_2_title AS section_label,
                   rule_section_label AS article_num,
                   section_title AS article_title,
                   section_content AS content_md
            FROM roc_codal 
            WHERE part_num = %s 
            ORDER BY 
                rule_num ASC,
                section_num ASC
        """, (book_num,))
        
        results = cur.fetchall()
        
        # Clean up Roman Numeral rules -> Arabic Numerals across all hierarchy boundaries
        fields_to_clean = ['title_label', 'chapter_label', 'section_label', 'book_label']
        for r in results:
            for field in fields_to_clean:
                if field in r and r[field]:
                    r[field] = clean_roman_rules(r[field])
        
        # Attach link counts (optional, but good for consistency)
        attach_link_counts(cur, results)
        
        return func.HttpResponse(json.dumps(results, default=str), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)

def attach_link_counts(cur, articles):
    if not articles:
        return

    article_nums = [str(a['article_num']).strip() for a in articles]
    
    # Query for counts grouped by article and paragraph
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = 'ROC' 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
        ORDER BY provision_id, target_paragraph_index
    """
    
    try:
        cur.execute(query, (article_nums,))
        rows = cur.fetchall()
        print(f"--- attach_link_counts: Fetched {len(rows)} matching rows from DB ---")
        
        link_map = {}
        for r in rows:
            art = str(r['provision_id']).strip()
            if art == 'Rule 10, Section 1':
                print(f"FOUND ROW in attach_link_counts for Rule 10, Section 1: {r}")
            idx = r['target_paragraph_index']
            count = r['link_count']
            
            if art not in link_map:
                link_map[art] = {}
            link_map[art][idx] = count
            
        for art in articles:
            anum = str(art['article_num']).strip()
            if anum in link_map:
                art['paragraph_links'] = link_map[anum]
            else:
                art['paragraph_links'] = {}
    except Exception as e:
        # Avoid breaking the main request if link count fails
        logging.error(f"Error attaching link counts: {e}")
        for art in articles:
            art['paragraph_links'] = {}

def natural_keys(text):
    import re
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

@roc_bp.route(route="roc/all", auth_level=func.AuthLevel.ANONYMOUS)
def get_roc_all(req: func.HttpRequest) -> func.HttpResponse:
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT *, 
                   part_num AS book,
                   part_title AS book_label,
                   rule_num AS title_num,
                   rule_title_full AS title_label,
                   group_1_title AS chapter_label,
                   group_2_title AS section_label,
                   rule_section_label AS article_num,
                   section_title AS article_title,
                   section_content AS content_md
            FROM roc_codal
        """)
        results = cur.fetchall()
        
        # Sort in memory to prevent integer cast overflows
        results.sort(key=lambda x: natural_keys(str(x['article_num']) if x['article_num'] else ""))
        
        # Clean up Roman Numeral rules -> Arabic Numerals across all hierarchy boundaries
        fields_to_clean = ['title_label', 'chapter_label', 'section_label', 'book_label']
        for r in results:
            for field in fields_to_clean:
                if field in r and r[field]:
                    r[field] = clean_roman_rules(r[field])
        
        attach_link_counts(cur, results)
        return func.HttpResponse(json.dumps(results, default=str), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)
