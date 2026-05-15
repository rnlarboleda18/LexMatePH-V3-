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
from concurrent.futures import ThreadPoolExecutor, as_completed

import azure.functions as func

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

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


def _get_ai_answer(query: str) -> str:
    """Call Gemini Flash directly for a fast 3-4 sentence answer."""
    try:
        import config
        from google import genai
        from google.genai import types

        if config.GCP_CREDENTIALS_FILE and os.path.exists(config.GCP_CREDENTIALS_FILE):
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.GCP_CREDENTIALS_FILE)

        client = genai.Client(
            vertexai=True,
            project=config.GCP_PROJECT,
            location=config.GCP_LOCATION,
        )
        cfg = types.GenerateContentConfig(
            temperature=0.1,
            system_instruction=AI_SEARCH_SYSTEM_PROMPT,
        )
        resp = client.models.generate_content(
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
    """Search sc_decided_cases via FTS + trigram. Returns top matching cases."""
    from db_pool import get_db_connection, put_db_connection
    from psycopg2.extras import RealDictCursor

    conn = None
    cases = []
    keywords = _extract_keywords(query)

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        fts_expr = """
            to_tsvector('english',
                COALESCE(full_title, '') || ' ' ||
                COALESCE(short_title, '') || ' ' ||
                COALESCE(case_number, '') || ' ' ||
                COALESCE(main_doctrine, '') || ' ' ||
                COALESCE(digest_facts, '')
            )
        """

        def _fts_query(term: str):
            sql = f"""
                SELECT id, short_title, case_number, date_str, main_doctrine,
                       subject, significance_category,
                       ts_rank_cd({fts_expr}, websearch_to_tsquery('english', %s)) AS score
                FROM sc_decided_cases
                WHERE {fts_expr} @@ websearch_to_tsquery('english', %s)
                ORDER BY score DESC
                LIMIT %s
            """
            cur.execute(sql, (term, term, limit))
            return cur.fetchall()

        # 1. FTS on raw query
        rows = _fts_query(query)

        # 2. FTS on extracted keywords (catches "what is mcburnie case" → "mcburnie")
        if not rows and keywords and keywords != query:
            rows = _fts_query(keywords)

        if not rows:
            # 3. Trigram fallback — try keywords first, then raw query
            for trig_term in ([keywords, query] if keywords != query else [query]):
                sql2 = """
                    SELECT id, short_title, case_number, date_str, main_doctrine,
                           subject, significance_category,
                           similarity(COALESCE(short_title,'') || ' ' || COALESCE(full_title,''), %s) AS score
                    FROM sc_decided_cases
                    WHERE short_title %% %s OR full_title %% %s
                    ORDER BY score DESC
                    LIMIT %s
                """
                try:
                    cur.execute(sql2, (trig_term, trig_term, trig_term, limit))
                    rows = cur.fetchall()
                except Exception:
                    rows = []
                if rows:
                    break

        for row in rows:
            cases.append({
                "id":                   row["id"],
                "short_title":          row["short_title"] or "",
                "case_number":          row["case_number"] or "",
                "date_str":             row["date_str"] or "",
                "main_doctrine":        (row["main_doctrine"] or "")[:200],
                "subject":              row["subject"] or "",
                "significance_category": row["significance_category"] or "",
                "score":                float(row["score"] or 0),
            })
        cur.close()
    except Exception as e:
        log.error(f"AI search DB query failed: {e}")
    finally:
        if conn:
            put_db_connection(conn)

    return cases


def _json(data: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )


@ai_search_bp.route(route="ai-search", methods=["POST", "OPTIONS"],
                    auth_level=func.AuthLevel.ANONYMOUS)
def ai_search(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
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

    # Run AI generation + DB search in parallel
    answer = ""
    cases = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_ai = executor.submit(_get_ai_answer, query)
        future_db = executor.submit(_search_cases_db, query, 3)

        try:
            cases = future_db.result(timeout=8)
        except Exception:
            cases = []

        try:
            answer = future_ai.result(timeout=20)
        except Exception:
            answer = ""

    return _json({"answer": answer, "cases": cases})
