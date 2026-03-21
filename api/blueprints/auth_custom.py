import azure.functions as func
import json
import os
import logging
import psycopg
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

auth_custom_bp = func.Blueprint()

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev_secret_key_change_in_prod")

@auth_custom_bp.route(route="register", methods=["POST"])
def register_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        email = req_body.get('email')
        password = req_body.get('password')

        if not email or not password:
            return func.HttpResponse(
                body=json.dumps({"error": "Email and password required"}),
                mimetype="application/json",
                status_code=400
            )

        # Hash password
        hashed_password = generate_password_hash(password)

        conn_string = os.environ.get("DB_CONNECTION_STRING")
        if not conn_string:
             return func.HttpResponse(
                body=json.dumps({"error": "Database connection not configured"}),
                mimetype="application/json",
                status_code=500
            )

        try:
            with psycopg.connect(conn_string) as conn:
                with conn.cursor() as cur:
                    # Check if user exists
                    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        return func.HttpResponse(
                            body=json.dumps({"error": "User already exists"}),
                            mimetype="application/json",
                            status_code=409
                        )

                    # Insert new user
                    cur.execute(
                        "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
                        (email, hashed_password)
                    )
                    user_id = cur.fetchone()[0]
                    conn.commit()
                    
                    return func.HttpResponse(
                        body=json.dumps({"message": "User registered successfully", "user_id": str(user_id)}),
                        mimetype="application/json",
                        status_code=201
                    )

        except Exception as e:
            logging.error(f"Database error: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Database error"}),
                mimetype="application/json",
                status_code=500
            )

    except Exception as e:
        logging.error(f"Registration error: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@auth_custom_bp.route(route="login", methods=["POST"])
def login_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        email = req_body.get('email')
        password = req_body.get('password')

        if not email or not password:
            return func.HttpResponse(
                body=json.dumps({"error": "Email and password required"}),
                mimetype="application/json",
                status_code=400
            )

        conn_string = os.environ.get("DB_CONNECTION_STRING")
        
        try:
            with psycopg.connect(conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
                    result = cur.fetchone()
                    
                    if not result:
                        return func.HttpResponse(
                            body=json.dumps({"error": "Invalid credentials"}),
                            mimetype="application/json",
                            status_code=401
                        )
                    
                    user_id, stored_hash = result
                    
                    # Verify password
                    if check_password_hash(stored_hash, password):
                        # Generate JWT
                        token_payload = {
                            "user_id": str(user_id),
                            "email": email,
                            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
                        }
                        token = jwt.encode(token_payload, SECRET_KEY, algorithm="HS256")
                        
                        return func.HttpResponse(
                            body=json.dumps({
                                "token": token,
                                "user": {
                                    "userId": str(user_id),
                                    "email": email
                                }
                            }),
                            mimetype="application/json",
                            status_code=200
                        )
                    else:
                        return func.HttpResponse(
                            body=json.dumps({"error": "Invalid credentials"}),
                            mimetype="application/json",
                            status_code=401
                        )

        except Exception as e:
            logging.error(f"Database error: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Database error"}),
                mimetype="application/json",
                status_code=500
            )

    except Exception as e:
        logging.error(f"Login error: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
