"""
Bar 2026 Reviewer — Azure Functions Blueprint
==============================================
Endpoints:
  GET  /api/reviewer/{subject}             — list all topics for a subject
  GET  /api/reviewer/{subject}/{topic_id}  — full reviewer section
  POST /api/reviewer/generate              — admin: trigger generation for a subject
  POST /api/reviewer/publish               — admin: publish / unpublish a topic
"""

import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional

import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor

from db_pool import get_db_connection, put_db_connection
from utils.clerk_auth import get_authenticated_user_id

bar_reviewer_bp = func.Blueprint()

# ── In-memory generation job state ────────────────────────────────────────────
_gen_lock = threading.Lock()
_gen_proc: Optional[subprocess.Popen] = None
_gen_log_path: Optional[Path] = None
_gen_state: dict = {
    "status": "idle",       # idle | running | done | failed
    "subject": None,
    "started_at": None,
    "finished_at": None,
    "last_exit_code": None,
}

VALID_SUBJECTS = {"political", "commercial", "civil", "labor", "criminal", "remedial"}


def _json(body, status=200):
    return func.HttpResponse(
        json.dumps(body, default=str),
        status_code=status,
        mimetype="application/json",
    )


def _check_admin(req: func.HttpRequest):
    """Returns (clerk_id, error_response). Callers must return error_response if not None."""
    clerk_id, err = get_authenticated_user_id(req)
    if err or not clerk_id:
        return None, _json({"error": "Unauthorized"}, 401)

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT is_admin FROM users WHERE clerk_id = %s", (clerk_id,))
            row = cur.fetchone()
            if not row or not row.get("is_admin"):
                return None, _json({"error": "Forbidden"}, 403)
    except Exception as exc:
        logging.error("Bar reviewer admin check error: %s", exc)
        return None, _json({"error": "Internal error"}, 500)
    finally:
        put_db_connection(conn)

    return clerk_id, None


def _tools_dir() -> Path:
    """Resolve path to api/tools/ regardless of running context."""
    return Path(__file__).resolve().parent.parent / "tools"


# ── GET /api/reviewer/{subject} ───────────────────────────────────────────────

@bar_reviewer_bp.route(route="reviewer/{subject}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_reviewer_subject(req: func.HttpRequest) -> func.HttpResponse:
    """
    Returns a list of all topics for the given subject, ordered by sort_order.
    Each item has: id, roman_num, topic_heading, sub_letter, sub_heading,
    sort_order, status, confidence, generated_at.
    Full content is excluded here for performance — use the topic detail endpoint.
    """
    subject = req.route_params.get("subject", "").lower()
    if subject not in VALID_SUBJECTS:
        return _json({"error": f"Unknown subject '{subject}'. Valid: {sorted(VALID_SUBJECTS)}"}, 400)

    # Optionally filter by status (default: published only for public access)
    status_filter = req.params.get("status", "published")
    show_all = req.params.get("all", "").lower() in ("1", "true")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if show_all:
            # Admin mode: show all statuses
            _, err = _check_admin(req)
            if err:
                return err
            cur.execute("""
                SELECT
                    id, subject_id, roman_num, topic_heading,
                    sub_letter, sub_heading, sort_order,
                    status, confidence, generated_at, generation_model,
                    case_cutoff
                FROM bar_reviewer_topics
                WHERE subject_id = %s
                ORDER BY sort_order ASC, roman_num ASC, sub_letter ASC NULLS FIRST
            """, (subject,))
        else:
            cur.execute("""
                SELECT
                    id, subject_id, roman_num, topic_heading,
                    sub_letter, sub_heading, sort_order,
                    status, confidence, generated_at, generation_model,
                    case_cutoff
                FROM bar_reviewer_topics
                WHERE subject_id = %s AND status = %s
                ORDER BY sort_order ASC, roman_num ASC, sub_letter ASC NULLS FIRST
            """, (subject, status_filter))

        rows = cur.fetchall()
        payload = [dict(r) for r in rows]
        cur.close()
        return _json({"subject": subject, "topics": payload, "count": len(payload)})

    except Exception as exc:
        logging.error("get_reviewer_subject error: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


# ── GET /api/reviewer/{subject}/{topic_id} ────────────────────────────────────

@bar_reviewer_bp.route(route="reviewer/{subject}/{topic_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_reviewer_topic(req: func.HttpRequest) -> func.HttpResponse:
    """
    Returns the full reviewer content for a single topic.
    Includes: doctrine_md, distinctions_md, memory_aid,
              key_provisions (JSONB), key_cases (JSONB), bar_questions (JSONB).
    """
    subject = req.route_params.get("subject", "").lower()
    topic_id = req.route_params.get("topic_id", "")

    if subject not in VALID_SUBJECTS:
        return _json({"error": f"Unknown subject '{subject}'"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                id, subject_id, roman_num, topic_heading,
                sub_letter, sub_heading, sort_order,
                doctrine_md, distinctions_md, memory_aid,
                key_provisions,
                CASE
                    WHEN jsonb_array_length(key_cases) > 30
                    THEN jsonb_path_query_array(key_cases, '$[0 to 29]')
                    ELSE key_cases
                END AS key_cases,
                bar_questions,
                status, confidence, generated_at, generation_model,
                case_cutoff
            FROM bar_reviewer_topics
            WHERE subject_id = %s AND id = %s
        """, (subject, topic_id))

        row = cur.fetchone()
        cur.close()

        if not row:
            return _json({"error": "Topic not found"}, 404)

        # Non-admin users can only see published topics
        if row["status"] != "published":
            _, err = _check_admin(req)
            if err:
                return _json({"error": "Topic not published"}, 404)

        return _json(dict(row))

    except Exception as exc:
        logging.error("get_reviewer_topic error: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


# ── POST /api/reviewer/generate ───────────────────────────────────────────────

@bar_reviewer_bp.route(route="reviewer/generate", methods=["POST", "GET"], auth_level=func.AuthLevel.ANONYMOUS)
def trigger_reviewer_generation(req: func.HttpRequest) -> func.HttpResponse:
    """
    Admin-only. Triggers the generation pipeline as a subprocess.
    Body: { "subject": "criminal", "only": "I.A" (optional), "force": true (optional) }
    GET with ?status=1 returns current job state.
    """
    # Status query
    if req.method == "GET" or req.params.get("status"):
        _, err = _check_admin(req)
        if err:
            return err
        with _gen_lock:
            state = dict(_gen_state)
        # Poll subprocess if running
        with _gen_lock:
            if _gen_proc is not None and _gen_proc.poll() is not None:
                _gen_state["last_exit_code"] = _gen_proc.returncode
                _gen_state["status"] = "done" if _gen_proc.returncode == 0 else "failed"
                from datetime import datetime, timezone
                _gen_state["finished_at"] = datetime.now(timezone.utc).isoformat()
        return _json({"generation": _gen_state})

    # Admin gate
    clerk_id, err = _check_admin(req)
    if err:
        return err

    try:
        body = req.get_json() or {}
    except Exception:
        body = {}

    subject = (body.get("subject") or req.params.get("subject", "")).lower()
    only    = body.get("only") or req.params.get("only", "")
    force   = body.get("force", False)

    if subject not in VALID_SUBJECTS:
        return _json({"error": f"Unknown subject. Valid: {sorted(VALID_SUBJECTS)}"}, 400)

    with _gen_lock:
        if _gen_state["status"] == "running":
            return _json({"error": "Generation already running", "state": _gen_state}, 409)

    tools_dir = _tools_dir()
    gen_script = tools_dir / "generate_bar_reviewer.py"
    if not gen_script.exists():
        return _json({"error": f"Generator script not found at {gen_script}"}, 500)

    python_exe = _resolve_python()
    cmd = [python_exe, str(gen_script), "--subject", subject]
    if only:
        cmd += ["--only", only]
    if force:
        cmd += ["--force"]

    log_path = tools_dir / f"gen_{subject}.log"

    try:
        log_fp = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            cwd=str(tools_dir.parent),   # run from api/ so local.settings.json is found
            stdout=log_fp,
            stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        logging.error("Failed to spawn generation subprocess: %s", exc)
        return _json({"error": f"Failed to start: {exc}"}, 500)

    from datetime import datetime, timezone
    with _gen_lock:
        _gen_proc         = proc
        _gen_log_path     = log_path
        _gen_state["status"]     = "running"
        _gen_state["subject"]    = subject
        _gen_state["started_at"] = datetime.now(timezone.utc).isoformat()
        _gen_state["finished_at"]    = None
        _gen_state["last_exit_code"] = None

    logging.info("Bar reviewer generation started: subject=%s pid=%d", subject, proc.pid)
    return _json({
        "message": f"Generation started for subject '{subject}'",
        "pid": proc.pid,
        "log": str(log_path),
        "state": _gen_state,
    }, 202)


# ── POST /api/reviewer/publish ────────────────────────────────────────────────

@bar_reviewer_bp.route(route="reviewer/publish", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def toggle_reviewer_publish(req: func.HttpRequest) -> func.HttpResponse:
    """
    Admin-only. Publish or unpublish a topic.
    Body: { "topic_id": "<uuid>", "status": "published" | "draft" }
    Also accepts: { "subject": "criminal", "publish_all": true }
    """
    clerk_id, err = _check_admin(req)
    if err:
        return err

    try:
        body = req.get_json() or {}
    except Exception:
        body = {}

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Bulk publish all topics in a subject
        if body.get("publish_all") and body.get("subject"):
            subject = body["subject"].lower()
            if subject not in VALID_SUBJECTS:
                return _json({"error": f"Unknown subject '{subject}'"}, 400)
            new_status = body.get("status", "published")
            if new_status not in ("published", "draft"):
                return _json({"error": "status must be 'published' or 'draft'"}, 400)
            cur.execute("""
                UPDATE bar_reviewer_topics
                SET status = %s, reviewed_by = %s, reviewed_at = NOW()
                WHERE subject_id = %s
                RETURNING id, roman_num, sub_letter, status
            """, (new_status, clerk_id, subject))
            updated = [dict(r) for r in cur.fetchall()]
            conn.commit()
            cur.close()
            return _json({"updated": len(updated), "status": new_status, "rows": updated})

        # Single topic
        topic_id  = body.get("topic_id", "")
        new_status = body.get("status", "published")
        if not topic_id:
            return _json({"error": "topic_id required"}, 400)
        if new_status not in ("published", "draft"):
            return _json({"error": "status must be 'published' or 'draft'"}, 400)

        cur.execute("""
            UPDATE bar_reviewer_topics
            SET status = %s, reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s
            RETURNING id, subject_id, roman_num, sub_letter, status
        """, (new_status, clerk_id, topic_id))
        row = cur.fetchone()
        if not row:
            return _json({"error": "Topic not found"}, 404)
        conn.commit()
        cur.close()
        return _json({"updated": dict(row)})

    except Exception as exc:
        if conn:
            conn.rollback()
        logging.error("toggle_reviewer_publish error: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


# ── POST /api/reviewer/flag ───────────────────────────────────────────────────

@bar_reviewer_bp.route(route="reviewer/flag", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def flag_reviewer_topic(req: func.HttpRequest) -> func.HttpResponse:
    """
    Authenticated user can flag a topic for admin review.
    Body: { "topic_id": "<uuid>", "note": "..." }
    """
    clerk_id, err = get_authenticated_user_id(req)
    if err or not clerk_id:
        return _json({"error": "Unauthorized"}, 401)

    try:
        body = req.get_json() or {}
    except Exception:
        body = {}

    topic_id = body.get("topic_id", "")
    note     = (body.get("note") or "").strip()

    if not topic_id:
        return _json({"error": "topic_id required"}, 400)
    if not note:
        return _json({"error": "note required"}, 400)
    if len(note) > 1000:
        return _json({"error": "note too long (max 1000 chars)"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO bar_reviewer_flags (topic_id, user_id, note)
            VALUES (%s, %s, %s)
            RETURNING id, created_at
        """, (topic_id, clerk_id, note))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return _json({"flagged": True, "flag_id": row["id"]}, 201)

    except Exception as exc:
        if conn:
            conn.rollback()
        logging.error("flag_reviewer_topic error: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


# ── GET /api/reviewer/gen/log ─────────────────────────────────────────────────

@bar_reviewer_bp.route(route="reviewer/gen/log", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_generation_log(req: func.HttpRequest) -> func.HttpResponse:
    """Admin-only. Return last N lines of the running (or most recent) generation log."""
    _, err = _check_admin(req)
    if err:
        return err

    with _gen_lock:
        log_path = _gen_log_path

    if not log_path or not Path(log_path).exists():
        return _json({"error": "No log available"}, 404)

    try:
        tail = int(req.params.get("tail", 200))
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return func.HttpResponse(
            "".join(lines[-tail:]),
            status_code=200,
            mimetype="text/plain",
        )
    except Exception as exc:
        return _json({"error": str(exc)}, 500)


# ── GET / PUT / DELETE /api/reviewer/{subject}/{topic_id}/annotations ─────────

@bar_reviewer_bp.route(
    route="reviewer/{subject}/{topic_id}/annotations",
    methods=["GET", "PUT", "DELETE"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def reviewer_annotations(req: func.HttpRequest) -> func.HttpResponse:
    """
    Per-user per-topic ink annotations (S Pen / Apple Pencil).

    GET    — load strokes for the authenticated user
    PUT    — upsert strokes  body: { "strokes": [...] }
    DELETE — clear all strokes for this user+topic
    """
    clerk_id, err = get_authenticated_user_id(req)
    if err or not clerk_id:
        return _json({"error": "Login required to access annotations"}, 401)

    topic_id = req.route_params.get("topic_id", "").strip()
    if not topic_id:
        return _json({"error": "topic_id required"}, 400)

    conn = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(cursor_factory=RealDictCursor)

        if req.method == "GET":
            cur.execute(
                "SELECT strokes FROM bar_topic_annotations "
                "WHERE topic_id = %s AND user_id = %s",
                (topic_id, clerk_id),
            )
            row = cur.fetchone()
            return _json({"strokes": row["strokes"] if row else []})

        elif req.method == "PUT":
            try:
                body = req.get_json() or {}
            except Exception:
                body = {}
            strokes = body.get("strokes", [])
            if not isinstance(strokes, list):
                return _json({"error": "strokes must be an array"}, 400)
            strokes_json = json.dumps(strokes)
            cur.execute(
                """
                INSERT INTO bar_topic_annotations (topic_id, user_id, strokes, updated_at)
                VALUES (%s, %s, %s::jsonb, NOW())
                ON CONFLICT (topic_id, user_id)
                DO UPDATE SET strokes = EXCLUDED.strokes, updated_at = NOW()
                RETURNING updated_at
                """,
                (topic_id, clerk_id, strokes_json),
            )
            updated = cur.fetchone()
            conn.commit()
            return _json({"saved": True, "updated_at": str(updated["updated_at"]) if updated else None})

        elif req.method == "DELETE":
            cur.execute(
                "DELETE FROM bar_topic_annotations WHERE topic_id = %s AND user_id = %s",
                (topic_id, clerk_id),
            )
            conn.commit()
            return _json({"cleared": True})

        else:
            return _json({"error": "Method not allowed"}, 405)

    except Exception as exc:
        if conn:
            conn.rollback()
        logging.error("reviewer_annotations error: %s", exc)
        return _json({"error": str(exc)}, 500)
    finally:
        if conn:
            put_db_connection(conn)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_python() -> str:
    """Find the Python executable — prefer the venv inside api/."""
    venv = Path(__file__).resolve().parent.parent / ".venv"
    candidates = [
        venv / "Scripts" / "python.exe",   # Windows
        venv / "bin" / "python",            # Unix
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    import sys
    return sys.executable
