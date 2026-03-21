import logging
import json
import os
import azure.functions as func
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

statutes_bp = func.Blueprint()

@statutes_bp.route(route="statutes", auth_level=func.AuthLevel.ANONYMOUS)
def get_statute(req: func.HttpRequest) -> func.HttpResponse:
    law = req.params.get('law')
    provision = req.params.get('provision')
    
    if not provision:
        return func.HttpResponse(json.dumps({"error": "Provision required"}), status_code=400)

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if law:
            cur.execute("SELECT * FROM statutes WHERE law_name ILIKE %s AND provision ILIKE %s", (f"%{law}%", f"%{provision}%"))
        else:
            cur.execute("SELECT * FROM statutes WHERE provision ILIKE %s", (f"%{provision}%",))
            
        result = cur.fetchone()
        
        if result:
            return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=200)
        else:
            return func.HttpResponse(json.dumps({"error": "Statute not found"}), status_code=404)

    except Exception as e:
        logging.error(f"Error fetching statute: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if cur: cur.close()
        if conn: put_db_connection(conn)
