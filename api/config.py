"""
Environment configuration for Bar Reviewer API
Handles switching between local development and production Azure environment
"""
import os

# Environment detection
IS_LOCAL_DEV = os.getenv("ENVIRONMENT", "production").lower() == "local"

# Database connection (LOCAL_DB_CONNECTION_STRING wins when ENVIRONMENT=local)
DB_CONNECTION_STRING = (
    os.getenv("LOCAL_DB_CONNECTION_STRING")
    if IS_LOCAL_DEV and os.getenv("LOCAL_DB_CONNECTION_STRING")
    else (os.getenv("DB_CONNECTION_STRING") or os.getenv("DATABASE_URL") or "")
)

# Redis configuration
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Cache TTL settings (in seconds)
CACHE_TTL_DECISIONS = int(os.getenv("CACHE_TTL_DECISIONS", "60"))  # 1 minute
CACHE_TTL_PONENTES = int(os.getenv("CACHE_TTL_PONENTES", "300"))  # 5 minutes
CACHE_TTL_FILTERS = int(os.getenv("CACHE_TTL_FILTERS", "300"))  # 5 minutes
# Proxied SC judiciary RSS (https://sc.judiciary.gov.ph/feed/) — refreshes when upstream publishes.
CACHE_TTL_SC_JUDICIARY_FEED = int(os.getenv("CACHE_TTL_SC_JUDICIARY_FEED", "900"))  # 15 minutes
# Table-backed payload is stable; digest merge is rare. Long TTL = fewer DB reads & Redis rebuilds.
CACHE_TTL_FLASHCARD_CONCEPTS = int(os.getenv("CACHE_TTL_FLASHCARD_CONCEPTS", "86400"))  # default 24h

# Redis key for GET /sc_decisions/flashcard_concepts — invalidate after populating flashcard_concepts (see scripts/populate_flashcard_concepts_from_digest.py)
FLASHCARD_CONCEPTS_CACHE_KEY = os.getenv(
    "FLASHCARD_CONCEPTS_CACHE_KEY",
    "flashcard_concepts:v11:bar_2026",
)

# Min TOS / syllabus match score for default flashcard deck (Bar-exam–aligned concepts only).
# Rows with a stored score below this are omitted unless ?bar_focus=0. Null score = legacy / unlabeled (still shown).
FLASHCARD_BAR_MIN_TOS_SCORE = float(os.getenv("FLASHCARD_BAR_MIN_TOS_SCORE", "0.1"))

# When true, GET /sc_decisions/flashcard_concepts keeps only rows with bar_2026_aligned=true (after other filters).
# Override per request with ?bar_2026_only=0 or =1. Rows with NULL bar_2026_aligned are excluded when strict.
FLASHCARD_BAR_2026_ONLY_DEFAULT = os.getenv("FLASHCARD_BAR_2026_ONLY", "").lower() in ("1", "true", "yes")

# Logging
import logging
logging.info(f"Environment: {'LOCAL' if IS_LOCAL_DEV else 'PRODUCTION'}")
logging.info(f"Database: {'Local PostgreSQL' if IS_LOCAL_DEV else 'Azure PostgreSQL'}")
logging.info(f"Redis: {'Enabled' if REDIS_ENABLED else 'Disabled'}")
