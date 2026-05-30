"""
AI Search — lightweight question-answering over the case digest.

POST /api/ai-search
  Body: { "query": "what is the tan-andal case?" }
  Response: { "answer": "...", "cases": [...] }

Runs Gemini Flash (no RAG) + PostgreSQL FTS in parallel.
Target latency: 3–5 seconds.
"""

import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, wait as futures_wait

import azure.functions as func

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
log = logging.getLogger(__name__)
ai_search_bp = func.Blueprint()

_QUESTION_WORDS = (
    "what", "who", "when", "where", "why", "how", "explain", "define",
    "describe", "discuss", "compare", "distinguish", "is there", "are there",
    "does", "can", "which", "give me", "tell me", "what's", "who's",
)

AI_SEARCH_SYSTEM_PROMPT = (
    "You are a Philippine legal expert. Answer the question in exactly 3–4 concise sentences: "
    "state the doctrine or ruling, name the controlling case with its exact G.R. number and year, "
    "and note any key exception, overruling, or evolution of the doctrine. "
    "If the question is about a specific statute, quote the key provision and its article number. "
    "Be precise and authoritative. Use proper legal terminology. "
    "If the question is not about Philippine law, say so in one sentence."
)


_NL_STOP_WORDS = {
    'what', 'who', 'when', 'where', 'why', 'how', 'explain', 'define',
    'describe', 'discuss', 'compare', 'distinguish', 'is', 'are', 'was',
    'were', 'does', 'did', 'can', 'could', 'would', 'should', 'there',
    'the', 'a', 'an', 'in', 'of', 'for', 'to', 'and', 'or', 'on', 'at',
    'by', 'from', 'with', 'about', 'give', 'me', 'tell', 'this', 'that',
    'these', 'those', 'its', 'their', 'case', 'cases', 'ruling', 'decision',
    'doctrine', 'rule',
}


def _extract_keywords(query: str) -> str:
    """Strip question/stop words; keep names, GR numbers, and meaningful terms."""
    # Preserve G.R. / GR number patterns as a single token
    gr = re.findall(r'g\.?\s*r\.?\s*no\.?\s*\d+', query, re.IGNORECASE)
    words = re.findall(r"[a-zA-Z']+", query.lower())
    keywords = [w for w in words if w not in _NL_STOP_WORDS and len(w) > 2]
    return ' '.join(gr + keywords) if gr else ' '.join(keywords)


def _looks_like_question(query: str) -> bool:
    q = query.lower().strip()
    if q.endswith("?"):
        return True
    if len(q.split()) < 3:
        return False
    return any(q.startswith(w) for w in _QUESTION_WORDS)


_gemini_client = None


def _get_gemini_client():
    """Return a cached Vertex AI GenAI client (one-time init per worker)."""
    global _gemini_client
    if _gemini_client is None:
        import config
        from google import genai
        _gemini_client = genai.Client(
            vertexai=True,
            project=config.GCP_PROJECT,
            location=config.GCP_LOCATION,
        )
    return _gemini_client


def _get_ai_answer(query: str) -> str:
    """Call Gemini Flash directly for a fast 3-4 sentence answer."""
    try:
        import config
        from google.genai import types

        cfg = types.GenerateContentConfig(
            temperature=0.1,
            system_instruction=AI_SEARCH_SYSTEM_PROMPT,
        )
        resp = _get_gemini_client().models.generate_content(
            model=config.GEMINI_FLASH_MODEL,
            contents=query,
            config=cfg,
        )
        return resp.text.strip() if resp.text else ""
    except Exception as e:
        import traceback
        log.error(f"AI search generation failed: {e}\n{traceback.format_exc()}")
        return ""


def _search_cases_db(query: str, limit: int = 3) -> list[dict]:
    """Search sc_decided_cases via ILIKE on extracted keywords.

    Avoids FTS / to_tsvector which requires a GIN index to be fast — without
    one it does a full table scan over digest_facts and times out on production.
    ILIKE on title columns is fast enough for LIMIT 3 and matches what
    supreme.py Tier 1/2 already does reliably.
    """
    from db_pool import get_db_connection, put_db_connection
    from psycopg2.extras import RealDictCursor

    conn = None
    cases = []
    keywords = _extract_keywords(query)
    tokens = [t for t in keywords.split() if len(t) > 2] if keywords else []

    if not tokens:
        return cases

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        select_cols = """
            id, short_title, case_number,
            TO_CHAR(date, 'YYYY-MM-DD') AS date_str,
            main_doctrine, subject, significance_category
        """

        # Tier A: any keyword appears in short_title OR full_title
        or_clauses = " OR ".join(
            ["short_title ILIKE %s OR full_title ILIKE %s" for _ in tokens]
        )
        params: list = []
        for t in tokens:
            params += [f"%{t}%", f"%{t}%"]

        cur.execute(
            f"SELECT {select_cols} FROM sc_decided_cases WHERE {or_clauses} ORDER BY date DESC LIMIT %s",
            params + [limit],
        )
        rows = cur.fetchall()

        # Tier B: keyword in main_doctrine if title search returned nothing
        if not rows:
            doc_clauses = " OR ".join(["main_doctrine ILIKE %s" for _ in tokens])
            doc_params = [f"%{t}%" for t in tokens] + [limit]
            try:
                cur.execute(
                    f"SELECT {select_cols} FROM sc_decided_cases WHERE {doc_clauses} ORDER BY date DESC LIMIT %s",
                    doc_params,
                )
                rows = cur.fetchall()
            except Exception:
                rows = []

        for row in rows:
            cases.append({
                "id":                    row["id"],
                "short_title":           row["short_title"] or "",
                "case_number":           row["case_number"] or "",
                "date_str":              row["date_str"] or "",
                "main_doctrine":         (row["main_doctrine"] or "")[:200],
                "subject":               row["subject"] or "",
                "significance_category": row["significance_category"] or "",
                "score":                 1.0,
            })
        cur.close()
    except Exception as e:
        log.error(f"AI search DB query failed: {e}")
    finally:
        if conn:
            put_db_connection(conn)

    return cases


_FRONTEND_ORIGIN = config.FRONTEND_URL


def _json(data: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": _FRONTEND_ORIGIN},
    )


@ai_search_bp.route(route="ai-search", methods=["POST", "OPTIONS"],
                    auth_level=func.AuthLevel.ANONYMOUS)
def ai_search(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": _FRONTEND_ORIGIN,
                "Access-Control-Allow-Methods": "POST",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
            },
        )

    try:
        body = req.get_json()
    except Exception:
        return _json({"error": "Invalid JSON"}, 400)

    query = (body.get("query") or "").strip()
    if not query:
        return _json({"error": "query is required"}, 400)
    if len(query) > 500:
        return _json({"error": "query too long"}, 400)

    # Only process natural language questions
    if not _looks_like_question(query):
        return _json({"answer": None, "cases": [], "skipped": True})

    # DB is fast (<1s) — run synchronously to avoid psycopg2 pool deadlock
    # when the pool is accessed from both the main thread and a thread-pool worker.
    # Only the Gemini call needs a thread + timeout.
    cases = _search_cases_db(query, 3)

    executor = ThreadPoolExecutor(max_workers=1)
    future_ai = executor.submit(_get_ai_answer, query)

    done, _ = futures_wait([future_ai], timeout=25)
    future_ai.cancel()

    try:
        answer = future_ai.result(timeout=0) if future_ai in done else ""
    except Exception:
        answer = ""

    executor.shutdown(wait=False)

    return _json({"answer": answer, "cases": cases})
