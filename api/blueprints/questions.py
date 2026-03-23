import azure.functions as func
import json
import os
import logging
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

questions_bp = func.Blueprint()

@questions_bp.route(route="questions", methods=["GET"])
def get_questions(req: func.HttpRequest) -> func.HttpResponse:
    conn = None
    cur = None
    try:
        # Parse query params
        year = req.params.get('year')
        subject = req.params.get('subject')
        limit = req.params.get('limit', '10000')
        
        query = """
            SELECT q.id, q.year, q.subject, q.text, q.source_label, a.text as answer
            FROM questions q
            LEFT JOIN answers a ON a.question_id = q.id
            WHERE 1=1
        """
        params = []

        if year:
            query += " AND q.year = %s"
            params.append(year)

        if subject:
            query += " AND q.subject = %s"
            params.append(subject)

        # Stable order — frontend shuffles per subject
        query += " ORDER BY q.year DESC, q.subject, q.id ASC LIMIT %s"
        params.append(int(limit))
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(query, params)
        results = cur.fetchall()
                
        return func.HttpResponse(
            body=json.dumps(results, default=str),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error getting questions: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
    finally:
        if cur: cur.close()
        if conn: put_db_connection(conn)
