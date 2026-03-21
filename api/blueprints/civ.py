
import logging
import json
import os
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

civ_bp = func.Blueprint()

@civ_bp.route(route="civ/book/{book_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_civ_by_book(req: func.HttpRequest) -> func.HttpResponse:
    book_num = req.route_params.get('book_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM civ_codal 
            WHERE book = %s 
            ORDER BY 
                CAST(REGEXP_REPLACE(article_num, '\D', '', 'g') AS INTEGER) ASC,
                article_num ASC
        """, (book_num,))
        
        results = cur.fetchall()
        
        # Attach link counts
        attach_link_counts(cur, results)
        attach_amendment_links(cur, results)
        
        return func.HttpResponse(json.dumps(results, default=str), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)

def attach_link_counts(cur, articles):
    if not articles:
        return

    article_nums = [str(a['article_num']) for a in articles]
    
    # Query for counts grouped by article and paragraph
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = 'CIV' 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
        ORDER BY provision_id, target_paragraph_index
    """
    
    try:
        cur.execute(query, (article_nums,))
        rows = cur.fetchall()
        
        # Map to structure: { "123": { "0": 5, "1": 2 } }
        link_map = {}
        for r in rows:
            art = r['provision_id']
            idx = r['target_paragraph_index']
            count = r['link_count']
            
            if art not in link_map:
                link_map[art] = {}
            link_map[art][idx] = count
            
        # Attach to articles
        for art in articles:
            anum = str(art['article_num'])
            if anum in link_map:
                art['paragraph_links'] = link_map[anum]
            else:
                art['paragraph_links'] = {}
    except Exception as e:
        logging.error(f"Error attaching links: {e}")
        # non-fatal, just plain articles
        for art in articles:
            art['paragraph_links'] = {}

def attach_amendment_links(cur, articles):
    """
    Attaches amendment information to articles if available in codal_amendments table.
    """
    if not articles:
        return

    article_nums = [str(a['article_num']) for a in articles]
    
    query = """
        SELECT provision_id, amendment_law, amendment_type, description, source_url, valid_from
        FROM codal_amendments
        WHERE statute_id = 'CIV'
          AND provision_id = ANY(%s)
    """
    
    try:
        cur.execute(query, (article_nums,))
        rows = cur.fetchall()
        
        amendment_map = {}
        for r in rows:
            art_num = r['provision_id']
            if art_num not in amendment_map:
                amendment_map[art_num] = []
            
            amendment_map[art_num].append({
                'amendment_law': r['amendment_law'],
                'amendment_type': r['amendment_type'],
                'description': r['description'],
                'source_url': r['source_url'],
                'valid_from': r['valid_from']
            })
            
        # Attach to articles
        for art in articles:
            anum = str(art['article_num'])
            if anum in amendment_map:
                art['amendment_links'] = amendment_map[anum]
            else:
                art['amendment_links'] = []
                
    except Exception as e:
        logging.error(f"Error attaching amendments: {e}")
        for art in articles:
            art['amendment_links'] = []

@civ_bp.route(route="civ/title/{title_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_civ_by_title(req: func.HttpRequest) -> func.HttpResponse:
    title_num = req.route_params.get('title_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check for book context
        book_param = req.params.get('book')
        
        query = "SELECT * FROM civ_codal WHERE title_num = %s"
        params = [title_num]
        
        if book_param:
            query += " AND book = %s"
            params.append(book_param)
            
        query += " ORDER BY CAST(REGEXP_REPLACE(article_num, '\D', '', 'g') AS INTEGER) ASC, article_num ASC"
            
        cur.execute(query, tuple(params))
        
        results = cur.fetchall()
        attach_link_counts(cur, results)
        attach_amendment_links(cur, results)
        return func.HttpResponse(json.dumps(results, default=str), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)

@civ_bp.route(route="civ/article/{article_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_civ_article(req: func.HttpRequest) -> func.HttpResponse:
    article_num = req.route_params.get('article_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM civ_codal 
            WHERE article_num = %s 
        """, (article_num,))
        
        result = cur.fetchone()
        if result:
            attach_link_counts(cur, [result])
            attach_amendment_links(cur, [result])
            return func.HttpResponse(json.dumps(result, default=str), mimetype="application/json")
        else:
             return func.HttpResponse(json.dumps({"error": "Not Found"}), status_code=404)
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)
