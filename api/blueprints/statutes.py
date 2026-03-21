import logging
import json
import os
import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor

statutes_bp = func.Blueprint()

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

@statutes_bp.route(route="statutes", auth_level=func.AuthLevel.ANONYMOUS)
def get_statute(req: func.HttpRequest) -> func.HttpResponse:
    law = req.params.get('law')
    provision = req.params.get('provision')
    
    if not provision:
        return func.HttpResponse(json.dumps({"error": "Provision required"}), status_code=400)

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if law:
            cur.execute("SELECT * FROM statutes WHERE law_name ILIKE %s AND provision ILIKE %s", (f"%{law}%", f"%{provision}%"))
        else:
            cur.execute("SELECT * FROM statutes WHERE provision ILIKE %s", (f"%{provision}%",))
            
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=200)
        else:
            return func.HttpResponse(json.dumps({"error": "Statute not found"}), status_code=404)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
