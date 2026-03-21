import logging
import json
import os
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor
from .codex import get_db_connection

labor_bp = func.Blueprint()

def attach_labor_link_counts(cur, articles):
    """Attach LAB jurisprudence link counts. Matches by raw article_num (e.g. '109')."""
    if not articles:
        return

    def clean_anum(anum):
        return str(anum).replace('Article', '').replace('.', '').strip()

    article_nums = [clean_anum(a['article_num']) for a in articles]
    
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = 'LAB' 
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
            anum = clean_anum(art['article_num'])
            if anum in link_map:
                art['paragraph_links'] = link_map[anum]
            else:
                art['paragraph_links'] = {}
    except Exception as e:
        logging.error(f"Error attaching LAB links: {e}")
        for art in articles:
            art['paragraph_links'] = {}

@labor_bp.route(route="labor/books", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def get_labor_books(req: func.HttpRequest) -> func.HttpResponse:
    """Returns the list of books in the Labor Code."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT DISTINCT book, book_label
            FROM labor_codal
            ORDER BY book NULLS FIRST
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        books = []
        for row in rows:
            book_num = row['book']
            book_label = row['book_label']
            if book_num:
                books.append({'id': str(book_num), 'name': f"Book {book_num} - {book_label}"})
            else:
                books.append({'id': "preliminary", 'name': book_label}) # "PRELIMINARY TITLE"
                
        return func.HttpResponse(json.dumps({'books': books}), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")

@labor_bp.route(route="labor/books/{book_id}", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def get_labor_book_content(req: func.HttpRequest) -> func.HttpResponse:
    """Returns the articles for a specific book in the Labor Code."""
    book_id = req.route_params.get('book_id')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if book_id == "preliminary":
            cur.execute("""
                SELECT id, book, book_label, title_num, title_label, chapter_num, chapter_label,
                       article_num, article_title, content_md, amendments, footnotes
                FROM labor_codal
                WHERE book IS NULL
                ORDER BY NULLIF(regexp_replace(article_num, '\D', '', 'g'), '')::int
            """)
        else:
            cur.execute("""
                SELECT id, book, book_label, title_num, title_label, chapter_num, chapter_label,
                       article_num, article_title, content_md, amendments, footnotes
                FROM labor_codal
                WHERE book = %s
                ORDER BY NULLIF(regexp_replace(article_num, '\D', '', 'g'), '')::int
            """, (book_id,))
            
        rows = cur.fetchall()
        
        # Structure the response
        articles = []
        for row in rows:
            art = dict(row)
            # Parse JSONB fields if they are returned as string (psycopg2 usually handles this, but be safe)
            if isinstance(art.get('amendments'), str):
                art['amendments'] = json.loads(art['amendments'])
            if isinstance(art.get('footnotes'), str):
                art['footnotes'] = json.loads(art['footnotes'])
                
            articles.append(art)
            
        attach_labor_link_counts(cur, articles)
        cur.close()
        conn.close()
            
        return func.HttpResponse(json.dumps({'articles': articles}, default=str), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")
