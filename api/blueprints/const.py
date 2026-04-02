
import logging
import json
import os
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

const_bp = func.Blueprint()

@const_bp.route(route="const/book/{book_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_const_by_book(req: func.HttpRequest) -> func.HttpResponse:
    book_num = req.route_params.get('book_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Constitution has no books, so we return everything if book_num is 1
        # Or just return everything regardless.
        
        # Natural sort for Roman-Number (I-1, I-2, II-1...)
        # We can just order by ID or use a custom sort in Python?
        # SQL sort might be tricky for "I-1".
        # Let's try simple sort for now.
        
        cur.execute("""
            SELECT * FROM consti_codal 
            WHERE book_code IS NULL OR book_code = 'CONST'
            ORDER BY list_order ASC 
        """)
        # Note: ID sorting works if we inserted in order (which we did).
        
        results = cur.fetchall()
        
        # Map for Frontend (Document View)
        mapped_results = []
        for r in results:
             new_r = dict(r)
             
             a_label = r['article_label'] or ""
             title = r['article_title'] or ""
             s_label = r['section_label'] or ""
             
             # stable title_label for the whole article
             # LexCodeStream hoists THIS when it changes
             title_label = None
             if a_label:
                 title_label = a_label
                 if title and title.upper() != a_label.upper():
                     title_label = f"{a_label}\n{title}"
             
             if "PREAMBLE" in a_label.upper():
                 title_label = "PREAMBLE"
                 article_num = ""
             elif s_label:
                 article_num = s_label.rstrip('.')
             else:
                 article_num = ""

             new_r['key_id'] = str(r['article_num'])  
             new_r['article_num'] = article_num 
             new_r['article_title'] = "" 
             new_r['title_label'] = title_label            # Hoisted as TITLE by LexCodeStream
             new_r['group_header'] = r.get('group_header') # Hoisted as BOOK by LexCodeStream
             new_r['section_label'] = None                 # Prevent redundant SECTION hoisting
             
             mapped_results.append(new_r)
        
        # Attach link counts to mapped results
        attach_link_counts(cur, mapped_results)
        
        return func.HttpResponse(json.dumps(mapped_results, default=str), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)


@const_bp.route(route="fc/all", auth_level=func.AuthLevel.ANONYMOUS)
def get_family_code(req: func.HttpRequest) -> func.HttpResponse:
    """Returns all Family Code articles."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM fc_codal
            WHERE book_code = 'FC'
            ORDER BY list_order ASC
        """)
        results = cur.fetchall()

        mapped_results = []
        prev_group = None
        for r in results:
            a_label = r.get('article_label') or '' # e.g. "TITLE I"
            title   = r.get('article_title') or '' # e.g. "MARRIAGE"
            s_label = r.get('section_label') or '' # e.g. "Chapter 1. Requisites of Marriage"

            new_r = dict(r)
            
            # Map Family Code hierarchy to match RPC hierarchy:
            new_r['book_label'] = "FAMILY CODE" 
            new_r['title_label'] = f"{a_label} {title}".strip()
            
            # Sub-sections (Chapters vs generic sections)
            if s_label.lower().startswith('chapter'):
                new_r['chapter_label'] = s_label
                new_r['section_label'] = None
            else:
                new_r['chapter_label'] = None
                new_r['section_label'] = s_label or None

            # Clear group_header and inline article_title to avoid duplication
            new_r['group_header']  = ""
            
            raw_article_num = r.get('article_num') or ''
            new_r['key_id'] = raw_article_num
            new_r['article_num'] = raw_article_num.split('-')[-1] if '-' in raw_article_num else raw_article_num
            new_r['article_title'] = ''
            mapped_results.append(new_r)

        # Attach jurisprudence link counts for Family Code
        attach_fam_link_counts(cur, mapped_results)

        return func.HttpResponse(json.dumps(mapped_results, default=str), mimetype="application/json")
    except Exception as e:
        logging.error(f"Error in get_family_code: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)

def attach_link_counts(cur, articles):
    """Attach CONST jurisprudence link counts. Matches by raw article_num (e.g. 'III-1')."""
    if not articles:
        return

    # Use key_id (raw DB article_num) for matching, not the display article_num
    key_ids = [str(a.get('key_id') or a['article_num']) for a in articles]
    
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = 'CONST' 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
        ORDER BY provision_id, target_paragraph_index
    """
    
    try:
        cur.execute(query, (key_ids,))
        rows = cur.fetchall()
        
        link_map = {}
        for r in rows:
            art = r['provision_id']
            idx = r['target_paragraph_index']
            count = r['link_count']
            if art not in link_map:
                link_map[art] = {}
            link_map[art][idx] = count
            
        for art in articles:
            key = str(art.get('key_id') or art['article_num'])
            if key in link_map:
                art['paragraph_links'] = link_map[key]
            else:
                art['paragraph_links'] = {}
    except Exception as e:
        logging.error(f"Error attaching CONST links: {e}")
        for art in articles:
            art['paragraph_links'] = {}


def attach_fam_link_counts(cur, articles):
    """Attach FAM jurisprudence link counts. Matches by the last segment of article_num (e.g. '220')."""
    if not articles:
        return

    # article_num in the FC mapped results is already the last segment (e.g. '220')
    article_nums = [str(a['article_num']) for a in articles]
    
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = 'FAM' 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
        ORDER BY provision_id, target_paragraph_index
    """
    
    try:
        cur.execute(query, (article_nums,))
        rows = cur.fetchall()
        
        link_map = {}
        for r in rows:
            art = r['provision_id']
            idx = r['target_paragraph_index']
            count = r['link_count']
            if art not in link_map:
                link_map[art] = {}
            link_map[art][idx] = count
            
        for art in articles:
            anum = str(art['article_num'])
            if anum in link_map:
                art['paragraph_links'] = link_map[anum]
            else:
                art['paragraph_links'] = {}
    except Exception as e:
        logging.error(f"Error attaching FAM links: {e}")
        for art in articles:
            art['paragraph_links'] = {}
