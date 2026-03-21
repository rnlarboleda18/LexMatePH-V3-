import os
import logging
import azure.functions as func


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
# Force redeploy - 2026-03-15 10:10

@app.route(route="ping", methods=["GET"])
def ping(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("pong", status_code=200)

import traceback
import sys
import os

import_error = None

try:
    from blueprints.questions import questions_bp
    from blueprints.grading import grading_bp
    from blueprints.schedule import schedule_bp
    from blueprints.user import user_bp
    from blueprints.auth_custom import auth_custom_bp
    from blueprints.supreme import supreme_bp
    from blueprints.ai_processor import ai_processor_bp
    from blueprints.statutes import statutes_bp
    from blueprints.codex import codex_bp
    from blueprints.rpc import rpc_bp
    from blueprints.civ import civ_bp
    from blueprints.const import const_bp
    from blueprints.labor import labor_bp
    from blueprints.audio_provider import audio_provider_bp
    from blueprints.playlists import playlists_bp
    from blueprints.clerk_webhook import clerk_webhook_bp
    from blueprints.roc import roc_bp

    app.register_functions(questions_bp)
    app.register_functions(grading_bp)
    app.register_functions(schedule_bp)
    app.register_functions(user_bp)
    app.register_functions(auth_custom_bp)
    app.register_functions(supreme_bp)
    app.register_functions(ai_processor_bp)
    app.register_functions(statutes_bp)
    app.register_functions(codex_bp)
    app.register_functions(rpc_bp)
    app.register_functions(civ_bp)
    app.register_functions(const_bp)
    app.register_functions(labor_bp)
    app.register_functions(audio_provider_bp)
    app.register_functions(playlists_bp)
    app.register_functions(clerk_webhook_bp)
    app.register_functions(roc_bp)
except Exception as e:
    import_error = f"Error during import/registration: {str(e)}\n{traceback.format_exc()}"

@app.route(route="debug_imports", methods=["GET"])
def debug_imports(req: func.HttpRequest) -> func.HttpResponse:
    if import_error:
        # Mask sensitive parts of connection string if present in error
        sanitized_error = import_error.replace(os.environ.get("DB_CONNECTION_STRING", "SECRET"), "REDACTED_CONN_STRING")
        return func.HttpResponse(sanitized_error, status_code=500, mimetype="text/plain")
    return func.HttpResponse("All imports successful.", status_code=200)

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("OK", status_code=200)

@app.route(route="health_db", methods=["GET"])
def health_db(req: func.HttpRequest) -> func.HttpResponse:
    from db_pool import get_db_connection, put_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return func.HttpResponse("Database connection successful.", status_code=200)
    except Exception as e:
        import traceback
        error_msg = f"Database connection failed: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        return func.HttpResponse(error_msg, status_code=500, mimetype="text/plain")
    finally:
        if conn:
            put_db_connection(conn)
