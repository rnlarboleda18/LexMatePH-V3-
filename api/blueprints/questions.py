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
        limit = req.params.get('limit', '100')
        
        query = "SELECT id, year, subject, text, source_label, (SELECT text FROM answers a WHERE a.question_id = questions.id LIMIT 1) as answer FROM questions WHERE 1=1"
        params = []
        
        if year:
            query += " AND year = %s"
            params.append(year)
        
        if subject:
            query += " AND subject = %s"
            params.append(subject)
            
        query += " ORDER BY RANDOM() LIMIT %s"
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
