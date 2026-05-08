"""
LexMate Legal Expert AI — Azure Functions blueprint.

Routes:
  POST /api/legal-chat                  — ask a legal question
  POST /api/legal-chat-clear            — clear session history
  GET  /api/legal-chat-status           — corpus / cost status (admin)
"""

import json
import logging
import os
import sys
import uuid

import azure.functions as func

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import (
    RAG_CORPUS_NAME, GCP_PROJECT, GCP_LOCATION,
    CACHE_SEMANTIC_THRESHOLD, CREDIT_TOTAL_EUR,
    GEMINI_PRO_MODEL, GEMINI_FLASH_MODEL,
)

log = logging.getLogger(__name__)
legal_chat_bp = func.Blueprint()

# In-memory session store — survives within a single function instance.
# For multi-instance deployments, swap for Redis (REDIS_URL is already in config).
_sessions: dict[str, list[dict]] = {}

# Lazily resolved — corpus name may come from env var or .corpus_name file
_corpus_name: str | None = None


def _get_corpus_name() -> str | None:
    global _corpus_name
    if _corpus_name:
        return _corpus_name
    if RAG_CORPUS_NAME:
        _corpus_name = RAG_CORPUS_NAME
        return _corpus_name
    # Fall back to persisted file
    try:
        from brain.rag.corpus import load_corpus_name
        _corpus_name = load_corpus_name()
    except Exception:
        pass
    return _corpus_name


def _session_history(session_id: str) -> list[dict]:
    return _sessions.get(session_id, [])


def _append_history(session_id: str, role: str, content: str) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append({"role": role, "content": content})
    _sessions[session_id] = _sessions[session_id][-10:]  # keep last 5 exchanges


def _get_user_id(req: func.HttpRequest) -> str | None:
    """Extract Clerk user ID from Authorization JWT."""
    try:
        from utils.clerk_auth import get_user_id_from_request
        return get_user_id_from_request(req)
    except Exception:
        return None


def _get_user_plan(user_id: str | None) -> str:
    if not user_id:
        return "guest"
    try:
        from db_pool import get_db_connection, put_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT subscription_status FROM users WHERE clerk_id = %s",
                    [user_id]
                )
                row = cur.fetchone()
                if row and row[0] == "active":
                    return "amicus"
        finally:
            put_db_connection(conn)
    except Exception as e:
        log.warning(f"Plan lookup failed: {e}")
    return "free"


def _json_response(data: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )


def _error(msg: str, status: int = 400) -> func.HttpResponse:
    return _json_response({"error": msg}, status)


# ── POST /api/legal-chat ───────────────────────────────────────────────────────

@legal_chat_bp.route(route="legal-chat", methods=["POST", "OPTIONS"],
                     auth_level=func.AuthLevel.ANONYMOUS)
def legal_chat(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204,
                                 headers={"Access-Control-Allow-Origin": "*",
                                          "Access-Control-Allow-Methods": "POST",
                                          "Access-Control-Allow-Headers": "Content-Type,Authorization"})

    try:
        body = req.get_json()
    except Exception:
        return _error("Invalid JSON body")

    question   = (body.get("message") or body.get("question") or "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())

    if not question:
        return _error("message is required")
    if len(question) > 2000:
        return _error("Question too long (max 2000 characters)")

    user_id = _get_user_id(req)
    plan    = _get_user_plan(user_id)
    user_key = user_id or session_id

    # ── Gate 1: Rate limit ──────────────────────────────────────────────────
    try:
        from brain.rag.ratelimit import check_rate_limit, record_usage
        limit = check_rate_limit(user_key, plan)
        if not limit["allowed"]:
            return _json_response({
                "error":          "Daily question limit reached",
                "limit":          limit.get("limit"),
                "resets_at":      limit.get("resets_at"),
                "upgrade_prompt": plan == "free",
            }, 429)
    except Exception as e:
        log.warning(f"Rate limit check failed (allowing): {e}")
        record_usage = lambda *a, **kw: None

    # ── Gate 2: Semantic cache ──────────────────────────────────────────────
    try:
        from brain.rag.cache import get_exact_cache, get_semantic_cache, save_to_cache

        cached = get_exact_cache(question)
        if cached:
            _append_history(session_id, "user", question)
            _append_history(session_id, "model", cached["answer"])
            return _json_response({**cached, "session_id": session_id,
                                   "cached": True, "cache_type": "exact"})

        cached = get_semantic_cache(question, threshold=CACHE_SEMANTIC_THRESHOLD)
        if cached:
            _append_history(session_id, "user", question)
            _append_history(session_id, "model", cached["answer"])
            return _json_response({**cached, "session_id": session_id,
                                   "cached": True, "cache_type": "semantic"})
    except Exception as e:
        log.warning(f"Cache lookup failed (continuing): {e}")
        save_to_cache = lambda *a, **kw: None

    # ── Gate 3 & 4: Pipeline + budget guard ────────────────────────────────
    from brain.rag.budget import get_pipeline, apply_budget_guard
    pipeline = get_pipeline(question, plan)
    pipeline = apply_budget_guard(pipeline)

    corpus_name = _get_corpus_name()
    if not corpus_name:
        return _error("Legal AI is not yet configured. Please try again later.", 503)

    chat_history = _session_history(session_id)

    # ── Retrieval ───────────────────────────────────────────────────────────
    try:
        from brain.rag.retrieval import retrieve
        retrieval_result = retrieve(
            question=question,
            corpus_name=corpus_name,
            pipeline=pipeline,
            chat_history=chat_history,
        )
    except Exception as e:
        log.error(f"Retrieval error: {e}")
        return _error("Could not retrieve legal sources. Please try again.", 502)

    # ── Generation ──────────────────────────────────────────────────────────
    try:
        from brain.rag.generation import generate
        gen_result = generate(
            question=question,
            retrieval_result=retrieval_result,
            chat_history=chat_history,
            plan=pipeline,
            user_plan=plan,
        )
    except Exception as e:
        log.error(f"Generation error: {e}")
        return _error("Could not generate answer. Please try again.", 502)

    # ── Record + cache ──────────────────────────────────────────────────────
    try:
        record_usage(user_key, plan, gen_result.get("tokens_used", 0))
    except Exception:
        pass

    try:
        save_to_cache(
            question=question,
            answer=gen_result["answer"],
            citations=gen_result["citations"],
            intent=retrieval_result["intent"],
        )
    except Exception:
        pass

    _append_history(session_id, "user", question)
    _append_history(session_id, "model", gen_result["answer"])

    # ── Build source list ───────────────────────────────────────────────────
    sources = []
    for chunk in retrieval_result.get("enriched_chunks", []):
        meta = chunk.get("doc_metadata") or {}
        sources.append({
            "title":     meta.get("short_title") or meta.get("title", ""),
            "gr_number": meta.get("gr_number", ""),
            "date":      meta.get("date", ""),
            "score":     round(chunk.get("rerank_score") or chunk.get("score", 0), 3),
        })

    return _json_response({
        "answer":     gen_result["answer"],
        "citations":  gen_result["citations"],
        "sources":    sources,
        "intent":     retrieval_result["intent"],
        "model_used": gen_result["model_used"],
        "session_id": session_id,
        "cached":     False,
        "warning":    gen_result.get("warning"),
    })


# ── POST /api/legal-chat-clear ─────────────────────────────────────────────────

@legal_chat_bp.route(route="legal-chat-clear", methods=["POST"],
                     auth_level=func.AuthLevel.ANONYMOUS)
def legal_chat_clear(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        session_id = body.get("session_id", "")
    except Exception:
        session_id = ""
    if session_id:
        _sessions.pop(session_id, None)
    return _json_response({"cleared": True, "session_id": session_id})


# ── GET /api/legal-chat-status ─────────────────────────────────────────────────

@legal_chat_bp.route(route="legal-chat-status", methods=["GET"],
                     auth_level=func.AuthLevel.ANONYMOUS)
def legal_chat_status(req: func.HttpRequest) -> func.HttpResponse:
    try:
        from brain.rag.budget import get_spend_pct
        spend_pct = get_spend_pct()
    except Exception:
        spend_pct = 0.0

    corpus_name = _get_corpus_name()
    return _json_response({
        "corpus_name":  corpus_name,
        "corpus_ready": bool(corpus_name),
        "spend_pct":    round(spend_pct, 2),
        "credit_eur":   CREDIT_TOTAL_EUR,
        "models": {
            "pro":   GEMINI_PRO_MODEL,
            "flash": GEMINI_FLASH_MODEL,
        },
        "active_sessions": len(_sessions),
    })
