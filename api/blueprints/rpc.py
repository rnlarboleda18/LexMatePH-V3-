
import logging
import json
import os
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

rpc_bp = func.Blueprint()

@rpc_bp.route(route="rpc/book/{book_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_rpc_by_book(req: func.HttpRequest) -> func.HttpResponse:
    book_num = req.route_params.get('book_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM rpc_codal 
            WHERE book = %s 
            ORDER BY 
                CAST(REGEXP_REPLACE(article_num, '\D', '', 'g') AS INTEGER) ASC,
                article_num ASC
        """, (book_num,))
        
        results = cur.fetchall()
        
        # Attach link counts
        attach_link_counts(cur, results)
        
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
        WHERE statute_id = 'RPC' 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
        ORDER BY provision_id, target_paragraph_index
    """
    
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

@rpc_bp.route(route="rpc/title/{title_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_rpc_by_title(req: func.HttpRequest) -> func.HttpResponse:
    title_num = req.route_params.get('title_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Note: Title Num is unique per book usually, but in RPC titles increment? 
        # Actually Book I and Book II might have overlapping Title numbers? 
        # RPC: Book I (Title 1-10?), Book II (Title 1-15?). 
        # Wait. RPC Book 2 starts with Title One ("Crimes against National Security").
        # So "Title 1" exists in BOTH Book 1 and Book 2.
        # So we likely need BOOK context too.
        # User request: "Fetch all articles for a specific Title (e.g., Crimes Against Property)"
        # Suggestion: Pass book_num as query param, or handle it.
        # Or maybe the User meant Title Label?
        
        # Let's check query params.
        book_param = req.params.get('book')
        
        query = "SELECT * FROM rpc_codal WHERE title_num = %s"
        params = [title_num]
        
        if book_param:
            query += " AND book = %s"
            params.append(book_param)
            
        query += " ORDER BY CAST(REGEXP_REPLACE(article_num, '\D', '', 'g') AS INTEGER) ASC, article_num ASC"
            
        cur.execute(query, tuple(params))
        
        results = cur.fetchall()
        attach_link_counts(cur, results)
        return func.HttpResponse(json.dumps(results, default=str), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)

@rpc_bp.route(route="rpc/article/{article_num}", auth_level=func.AuthLevel.ANONYMOUS)
def get_rpc_article(req: func.HttpRequest) -> func.HttpResponse:
    article_num = req.route_params.get('article_num')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM rpc_codal 
            WHERE article_num = %s 
        """, (article_num,))
        
        result = cur.fetchone()
        if result:
            attach_link_counts(cur, [result])
            return func.HttpResponse(json.dumps(result, default=str), mimetype="application/json")
        else:
             return func.HttpResponse(json.dumps({"error": "Not Found"}), status_code=404)
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if 'conn' in locals(): put_db_connection(conn)
