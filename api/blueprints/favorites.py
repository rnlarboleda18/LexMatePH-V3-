"""
Favorites blueprint — per-user starred items.

Routes (all require Clerk JWT; subscriber or admin only):
  GET  /api/favorites/ids?type={content_type}          → ["id1", ...]
  GET  /api/favorites?type={content_type}              → [{content_type, content_id, title, subtitle, created_at}, ...]
  POST /api/favorites   {content_type, content_id, title?, subtitle?}  → {ok: true}
  DELETE /api/favorites {content_type, content_id}                     → {ok: true}
"""

import json
import logging
import traceback
import azure.functions as func

from db_pool import get_db_connection, put_db_connection
from utils.clerk_auth import get_authenticated_user_id

favorites_bp = func.Blueprint()

_tables_ensured = False

_ENSURE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS user_favorites (
    id           SERIAL PRIMARY KEY,
    user_id      VARCHAR(255) NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('case', 'bar_question', 'flashcard')),
    content_id   TEXT NOT NULL,
    title        TEXT,
    subtitle     TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, content_type, content_id)
);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'user_favorites' AND indexname = 'user_favorites_user_type_idx'
    ) THEN
        CREATE INDEX user_favorites_user_type_idx ON user_favorites(user_id, content_type);
    END IF;
END $$;
"""

VALID_TYPES = {'case', 'bar_question', 'flashcard'}


def _json(body, status=200):
    return func.HttpResponse(
        json.dumps(body, default=str),
        status_code=status,
        mimetype="application/json",
    )


def _ensure_tables(conn):
    global _tables_ensured
    if _tables_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(_ENSURE_TABLES_SQL)
        conn.commit()
        _tables_ensured = True
        logging.info("user_favorites table ensured.")
    except Exception as e:
        logging.error("Failed to ensure user_favorites table: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        cur.close()


def _check_access(req):
    """Returns (clerk_id, error_response). Checks auth + subscriber/admin gate."""
    clerk_id, err = get_authenticated_user_id(req)
    if not clerk_id:
        return None, _json({"error": "Unauthorized", "detail": err}, 401)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_admin, subscription_status FROM users WHERE clerk_id = %s",
                (clerk_id,),
            )
            row = cur.fetchone()
            if not row:
                return None, _json({"error": "Forbidden"}, 403)
            is_admin, sub_status = row
            if not is_admin and sub_status != 'active':
                return None, _json({"error": "Forbidden", "detail": "Subscription required"}, 403)
    except Exception as exc:
        logging.error("_check_access DB error: %s", exc)
        return None, _json({"error": "Server error"}, 500)
    finally:
        put_db_connection(conn)

    return clerk_id, None


@favorites_bp.route(route="favorites/ids", methods=["GET"])
def get_favorite_ids(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    content_type = req.params.get("type")
    if content_type not in VALID_TYPES:
        return _json({"error": f"type must be one of {sorted(VALID_TYPES)}"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content_id FROM user_favorites WHERE user_id = %s AND content_type = %s",
                (clerk_id, content_type),
            )
            ids = [row[0] for row in cur.fetchall()]
        return _json(ids)
    except Exception as e:
        logging.error("get_favorite_ids error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


@favorites_bp.route(route="favorites", methods=["GET"])
def get_favorites(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    content_type = req.params.get("type")
    if content_type not in VALID_TYPES:
        return _json({"error": f"type must be one of {sorted(VALID_TYPES)}"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content_type, content_id, title, subtitle, created_at
                FROM user_favorites
                WHERE user_id = %s AND content_type = %s
                ORDER BY created_at DESC
                """,
                (clerk_id, content_type),
            )
            rows = cur.fetchall()
        items = [
            {
                "content_type": r[0],
                "content_id": r[1],
                "title": r[2],
                "subtitle": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
        return _json(items)
    except Exception as e:
        logging.error("get_favorites error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


@favorites_bp.route(route="favorites", methods=["POST"])
def add_favorite(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    try:
        body = req.get_json()
    except Exception:
        return _json({"error": "Invalid JSON body"}, 400)

    content_type = body.get("content_type")
    content_id = body.get("content_id")
    if content_type not in VALID_TYPES or not content_id:
        return _json({"error": "content_type and content_id required"}, 400)

    title = body.get("title") or None
    subtitle = body.get("subtitle") or None

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_favorites (user_id, content_type, content_id, title, subtitle)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, content_type, content_id) DO NOTHING
                """,
                (clerk_id, content_type, str(content_id), title, subtitle),
            )
            conn.commit()
        return _json({"ok": True})
    except Exception as e:
        logging.error("add_favorite error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


@favorites_bp.route(route="favorites", methods=["DELETE"])
def remove_favorite(req: func.HttpRequest) -> func.HttpResponse:
    clerk_id, err = _check_access(req)
    if err:
        return err

    try:
        body = req.get_json()
    except Exception:
        return _json({"error": "Invalid JSON body"}, 400)

    content_type = body.get("content_type")
    content_id = body.get("content_id")
    if content_type not in VALID_TYPES or not content_id:
        return _json({"error": "content_type and content_id required"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_favorites WHERE user_id = %s AND content_type = %s AND content_id = %s",
                (clerk_id, content_type, str(content_id)),
            )
            conn.commit()
        return _json({"ok": True})
    except Exception as e:
        logging.error("remove_favorite error: %s\n%s", e, traceback.format_exc())
        return _json({"error": str(e)}, 500)
    finally:
        if conn:
            put_db_connection(conn)
