"""
Two-level semantic cache for legal chat answers.
Level 1: exact hash match (free)
Level 2: embedding similarity match (cheap — one embed call)
Uses PostgreSQL + pgvector on the existing DB.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras

import config
from db_pool import get_db_conn

log = logging.getLogger(__name__)

CACHE_TTL = {
    "doctrine_lookup":  timedelta(days=30),
    "statute_lookup":   timedelta(days=30),
    "case_search":      timedelta(days=7),
    "comparison":       timedelta(days=7),
    "general":          timedelta(days=7),
}

# ── Ensure cache table exists ──────────────────────────────────────────────────

INIT_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS legal_chat_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_hash   VARCHAR(64) UNIQUE,
    question_text   TEXT,
    answer          TEXT,
    citations       JSONB,
    intent          VARCHAR(50),
    hit_count       INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    invalidated     BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_chat_cache_hash ON legal_chat_cache(question_hash);
CREATE INDEX IF NOT EXISTS idx_chat_cache_expires ON legal_chat_cache(expires_at) WHERE NOT invalidated;
"""

_table_init_done = False


def _ensure_table():
    global _table_init_done
    if _table_init_done:
        return
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(INIT_SQL)
            conn.commit()
        _table_init_done = True
    except Exception as e:
        log.warning(f"Cache table init failed (pgvector may not be installed): {e}")
        _table_init_done = True  # Don't retry on every request


def _hash(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()


# ── Level 1: Exact match ───────────────────────────────────────────────────────

def get_exact_cache(question: str) -> dict | None:
    _ensure_table()
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    UPDATE legal_chat_cache
                    SET hit_count = hit_count + 1
                    WHERE question_hash = %s
                      AND NOT invalidated
                      AND (expires_at IS NULL OR expires_at > NOW())
                    RETURNING answer, citations, intent
                """, [_hash(question)])
                conn.commit()
                row = cur.fetchone()
                if row:
                    return {
                        "answer":    row["answer"],
                        "citations": row["citations"] or [],
                        "intent":    row["intent"],
                    }
    except Exception as e:
        log.warning(f"Exact cache lookup failed: {e}")
    return None


# ── Level 2: Semantic match ────────────────────────────────────────────────────

def get_semantic_cache(question: str, threshold: float = 0.92) -> dict | None:
    """
    Embed the question and find a similar cached answer.
    Falls back gracefully if pgvector isn't available.
    """
    _ensure_table()

    try:
        embedding = _embed(question)
        if not embedding:
            return None

        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT answer, citations, intent,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM legal_chat_cache
                    WHERE NOT invalidated
                      AND (expires_at IS NULL OR expires_at > NOW())
                      AND embedding IS NOT NULL
                      AND 1 - (embedding <=> %s::vector) > %s
                    ORDER BY similarity DESC
                    LIMIT 1
                """, [str(embedding), str(embedding), threshold])
                row = cur.fetchone()
                if row:
                    return {
                        "answer":     row["answer"],
                        "citations":  row["citations"] or [],
                        "intent":     row["intent"],
                        "similarity": float(row["similarity"]),
                    }
    except Exception as e:
        log.warning(f"Semantic cache lookup failed: {e}")
    return None


def save_to_cache(
    question: str,
    answer: str,
    citations: list,
    intent: str,
) -> None:
    """Save a question-answer pair to both exact and semantic cache."""
    _ensure_table()

    try:
        ttl = CACHE_TTL.get(intent, timedelta(days=7))
        expires_at = datetime.utcnow() + ttl
        embedding  = _embed(question)

        with get_db_conn() as conn:
            with conn.cursor() as cur:
                if embedding:
                    cur.execute("""
                        INSERT INTO legal_chat_cache
                            (question_hash, question_text, answer, citations, intent, expires_at, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                        ON CONFLICT (question_hash) DO UPDATE
                        SET answer = EXCLUDED.answer,
                            citations = EXCLUDED.citations,
                            expires_at = EXCLUDED.expires_at,
                            invalidated = FALSE
                    """, [
                        _hash(question), question, answer,
                        json.dumps(citations), intent, expires_at,
                        str(embedding),
                    ])
                else:
                    cur.execute("""
                        INSERT INTO legal_chat_cache
                            (question_hash, question_text, answer, citations, intent, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (question_hash) DO UPDATE
                        SET answer = EXCLUDED.answer,
                            citations = EXCLUDED.citations,
                            expires_at = EXCLUDED.expires_at,
                            invalidated = FALSE
                    """, [_hash(question), question, answer, json.dumps(citations), intent, expires_at])
            conn.commit()
    except Exception as e:
        log.warning(f"Cache save failed: {e}")


def invalidate_by_topics(topics: list[str]) -> int:
    """Invalidate cache entries related to specific topics (call after corpus update)."""
    try:
        patterns = [f"%{t}%" for t in topics]
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE legal_chat_cache
                    SET invalidated = TRUE
                    WHERE question_text ILIKE ANY(%s)
                       OR answer ILIKE ANY(%s)
                """, [patterns, patterns])
                count = cur.rowcount
            conn.commit()
        log.info(f"Invalidated {count} cache entries for topics: {topics}")
        return count
    except Exception as e:
        log.warning(f"Cache invalidation failed: {e}")
        return 0


def _embed(text: str) -> list[float] | None:
    """Generate an embedding using Gemini text-embedding-004 via Vertex AI."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            vertexai=True,
            project=config.GCP_PROJECT,
            location=config.GCP_LOCATION,
        )
        resp = client.models.embed_content(
            model="text-embedding-004",
            contents=text[:2000],  # embedding model token limit
        )
        return resp.embeddings[0].values
    except Exception as e:
        log.warning(f"Embedding failed: {e}")
        return None
