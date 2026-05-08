"""
Per-user daily rate limiting for the legal chat endpoint.
Stored in PostgreSQL to survive restarts and work across instances.
"""

import logging
from datetime import date, datetime

import psycopg2

import config
from db_pool import get_db_conn

log = logging.getLogger(__name__)

LIMITS = {
    "guest":  config.RATE_LIMIT_GUEST,
    "free":   config.RATE_LIMIT_FREE,
    "amicus": config.RATE_LIMIT_AMICUS,
    "admin":  -1,
}

INIT_SQL = """
CREATE TABLE IF NOT EXISTS legal_chat_usage (
    user_key        VARCHAR(128) NOT NULL,
    usage_date      DATE NOT NULL,
    question_count  INT DEFAULT 0,
    pro_count       INT DEFAULT 0,
    tokens_used     BIGINT DEFAULT 0,
    PRIMARY KEY (user_key, usage_date)
);
CREATE INDEX IF NOT EXISTS idx_chat_usage_date ON legal_chat_usage(usage_date);
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
        log.warning(f"Usage table init failed: {e}")
        _table_init_done = True


def check_rate_limit(user_key: str, plan: str) -> dict:
    """
    Check if the user has exceeded their daily limit.
    Returns {allowed, limit, used, resets_at, upgrade_prompt}
    """
    _ensure_table()
    limit = LIMITS.get(plan, config.RATE_LIMIT_FREE)

    if limit == -1:
        return {"allowed": True, "limit": -1, "used": 0}

    today = date.today()

    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT question_count FROM legal_chat_usage
                    WHERE user_key = %s AND usage_date = %s
                """, [user_key, today])
                row = cur.fetchone()
                used = row[0] if row else 0

        if used >= limit:
            return {
                "allowed":        False,
                "limit":          limit,
                "used":           used,
                "resets_at":      str(today + __import__("datetime").timedelta(days=1)),
                "upgrade_prompt": plan == "free",
            }

        return {"allowed": True, "limit": limit, "used": used}

    except Exception as e:
        log.warning(f"Rate limit check failed (allowing): {e}")
        return {"allowed": True, "limit": limit, "used": 0}


def record_usage(user_key: str, plan: str, tokens: int = 0, is_pro: bool = False) -> None:
    """Increment usage counters after a successful response."""
    _ensure_table()
    today = date.today()

    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO legal_chat_usage (user_key, usage_date, question_count, pro_count, tokens_used)
                    VALUES (%s, %s, 1, %s, %s)
                    ON CONFLICT (user_key, usage_date) DO UPDATE
                    SET question_count = legal_chat_usage.question_count + 1,
                        pro_count      = legal_chat_usage.pro_count + EXCLUDED.pro_count,
                        tokens_used    = legal_chat_usage.tokens_used + EXCLUDED.tokens_used
                """, [user_key, today, 1 if is_pro else 0, tokens])
            conn.commit()
    except Exception as e:
        log.warning(f"Usage recording failed: {e}")
