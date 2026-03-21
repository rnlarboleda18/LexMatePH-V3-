import azure.functions as func
import json
import os
import psycopg
import logging
from datetime import date, time

schedule_bp = func.Blueprint()

@schedule_bp.route(route="schedule", methods=["GET"])
async def get_schedule(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Fetch active schedule
        query = """
            SELECT 
                es.id, 
                bs.name as subject_name, 
                es.exam_date, 
                es.start_time, 
                es.end_time
            FROM exam_schedules es
            JOIN bar_subjects bs ON es.subject_id = bs.id
            JOIN bar_exam_cycles bec ON es.cycle_id = bec.id
            WHERE bec.is_active = TRUE
            ORDER BY es.exam_date, es.start_time
        """
        
        results = []
        # Using synchronous connection for now to match other blueprints
        # In a real async app, we'd use the pool
        conn_string = os.environ.get("DB_CONNECTION_STRING")
        if not conn_string:
             # Fallback for local dev if env var missing (should be there though)
             return func.HttpResponse(json.dumps({"error": "DB_CONNECTION_STRING missing"}), status_code=500)

        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                
                for row in rows:
                    item = dict(zip(columns, row))
                    # Serialize date/time objects
                    if isinstance(item['exam_date'], date):
                        item['exam_date'] = item['exam_date'].isoformat()
                    if isinstance(item['start_time'], time):
                        item['start_time'] = item['start_time'].isoformat()
                    if isinstance(item['end_time'], time):
                        item['end_time'] = item['end_time'].isoformat()
                    results.append(item)
        
        return func.HttpResponse(
            body=json.dumps(results),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error getting schedule: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
