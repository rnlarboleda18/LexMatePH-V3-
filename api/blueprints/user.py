import azure.functions as func
import json
import os
import logging
import psycopg

from utils.clerk_auth import get_authenticated_user_id

user_bp = func.Blueprint()

@user_bp.route(route="history", methods=["GET"])
def get_user_history(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get User ID from Clerk Auth Helper
        user_id = get_authenticated_user_id(req)
        
        if not user_id:
             return func.HttpResponse(
                body=json.dumps({"error": "Unauthorized"}),
                mimetype="application/json",
                status_code=401
            )

        conn_string = os.environ.get("DB_CONNECTION_STRING")
        if not conn_string:
             return func.HttpResponse(
                body=json.dumps({"error": "Database connection not configured"}),
                mimetype="application/json",
                status_code=500
            )

        history = []
        try:
            with psycopg.connect(conn_string) as conn:
                with conn.cursor() as cur:
                    # Fetch scores for the user
                    cur.execute("""
                        SELECT 
                            id, 
                            subject_name, 
                            raw_score, 
                            ai_feedback, 
                            created_at,
                            question_id
                        FROM user_mock_scores 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC
                    """, (user_id,))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        history.append({
                            "id": str(row[0]),
                            "subject": row[1],
                            "score": float(row[2]) if row[2] is not None else 0,
                            "feedback": row[3],
                            "date": row[4].isoformat() if row[4] else None,
                            "question_id": row[5]
                        })
                        
        except Exception as e:
            logging.error(f"Database error: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Database error fetching history"}),
                mimetype="application/json",
                status_code=500
            )

        return func.HttpResponse(
            body=json.dumps(history),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"History error: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
