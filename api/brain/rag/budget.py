"""
Budget guard and pipeline router for legal chat.
Tracks token spend and downgrades model pipeline when approaching credit limit.
"""

import logging
from datetime import date

import config
from db_pool import get_db_conn

log = logging.getLogger(__name__)

# Approximate EUR cost per token (Gemini 2.5 Flash input ~$0.15/M, Pro ~$1.25/M)
COST_PER_TOKEN_FLASH = 0.00000015   # EUR
COST_PER_TOKEN_PRO   = 0.00000125   # EUR

PIPELINES = {
    "lite": {
        "use_hyde":      False,
        "use_rerank":    True,
        "top_k":         12,
        "load_full_doc": False,
        "model":         config.GEMINI_PRO_MODEL,
    },
    # GCS full-doc loading removed from standard to keep latency under 30s.
    # RAG chunks alone provide enough context for most doctrinal questions.
    "standard": {
        "use_hyde":      True,
        "use_rerank":    True,
        "top_k":         20,
        "load_full_doc": False,
        "model":         config.GEMINI_PRO_MODEL,
    },
    "full": {
        "use_hyde":      True,
        "use_rerank":    True,
        "top_k":         30,
        "load_full_doc": True,
        "model":         config.GEMINI_PRO_MODEL,
    },
}


_complexity_signals = {
    "compare":            5,
    "distinguish":        4,
    "reconcile":          4,
    "evolution":          4,
    "history of":         4,
    "explain":            3,
    "leading case":       3,
    "landmark":           3,
    "doctrine":           3,
    "elements":           3,
    "requisites":         3,
    "what is":            2,
    "define":             1,
    "article":            1,
    "section":            1,
    "meaning":            1,
}


def _score_complexity(question: str) -> int:
    q = question.lower()
    score = 2
    for signal, val in _complexity_signals.items():
        if signal in q:
            score = max(score, val)
    if len(question.split()) > 25:
        score = min(score + 1, 5)
    return score


def get_pipeline(question: str, plan: str) -> dict:
    """Select retrieval pipeline based on question complexity and user plan."""
    score = _score_complexity(question)

    # Non-paying users never get Pro model or full pipeline
    if plan not in ("amicus", "admin"):
        score = min(score, config.COMPLEXITY_FLASH_MAX)

    if score <= 2:
        p = PIPELINES["lite"].copy()
    elif score == 3:
        p = PIPELINES["standard"].copy()
    else:
        p = PIPELINES["full"].copy()

    p["complexity"] = score
    return p


def apply_budget_guard(pipeline: dict) -> dict:
    """Downgrade pipeline based on current credit spend."""
    pct = get_spend_pct()
    pipeline = pipeline.copy()

    if pct >= config.BUDGET_EMERGENCY_PCT:
        log.warning(f"Budget EMERGENCY ({pct:.1f}%): switching to lite pipeline")
        pipeline.update(PIPELINES["lite"])
        pipeline["budget_downgraded"] = "emergency"

    elif pct >= config.BUDGET_CAUTION_PCT:
        log.warning(f"Budget CAUTION ({pct:.1f}%): disabling HyDE")
        pipeline["use_hyde"] = False
        pipeline["budget_downgraded"] = "caution"

    elif pct >= config.BUDGET_WARN_PCT:
        log.info(f"Budget WARNING ({pct:.1f}%): disabling HyDE")
        pipeline["use_hyde"] = False
        pipeline["budget_downgraded"] = "warn"

    return pipeline


def get_spend_pct() -> float:
    """Estimate % of credit used based on recorded tokens."""
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(tokens_used), 0)
                    FROM legal_chat_usage
                    WHERE usage_date >= date_trunc('month', CURRENT_DATE)
                """)
                total_tokens = float(cur.fetchone()[0])

        # Assume 80% Flash, 20% Pro for cost estimate
        estimated_eur = (
            total_tokens * 0.8 * COST_PER_TOKEN_FLASH +
            total_tokens * 0.2 * COST_PER_TOKEN_PRO
        )
        return min((estimated_eur / config.CREDIT_TOTAL_EUR) * 100, 100.0)

    except Exception as e:
        log.warning(f"Spend calculation failed: {e}")
        return 0.0


def record_tokens(tokens: int) -> None:
    """Record token usage for budget tracking (called from blueprint)."""
    # Token recording is handled by ratelimit.record_usage — no separate call needed
    pass
