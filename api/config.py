"""
Environment configuration for Bar Reviewer API
Handles switching between local development and production Azure environment
"""
import os


# Environment detection (developer workstation vs deployed app — unrelated to DB host)
IS_LOCAL_DEV = os.getenv("ENVIRONMENT", "production").lower() == "local"

# Cloud Postgres only (Azure). Set DB_CONNECTION_STRING / DATABASE_URL in Application Settings or
# api/local.settings.json — including local `func start`. Local mirrors use pg_restore workflows, not this URI swap.
DB_CONNECTION_STRING = (os.getenv("DB_CONNECTION_STRING") or os.getenv("DATABASE_URL") or "").strip()

# Optional local Postgres URI for admin backup mirror (pg_restore only). Not used for API queries.
LOCAL_DB_CONNECTION_STRING = (os.getenv("LOCAL_DB_CONNECTION_STRING") or "").strip()

# Redis configuration
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Cache TTL settings (in seconds)
CACHE_TTL_DECISIONS = int(os.getenv("CACHE_TTL_DECISIONS", "60"))  # 1 minute
CACHE_TTL_DECISION_DETAIL = int(os.getenv("CACHE_TTL_DECISION_DETAIL", "600"))  # 10 minutes — case detail rarely changes
CACHE_TTL_PONENTES = int(os.getenv("CACHE_TTL_PONENTES", "300"))  # 5 minutes
CACHE_TTL_FILTERS = int(os.getenv("CACHE_TTL_FILTERS", "300"))  # 5 minutes
# Proxied SC judiciary RSS (https://sc.judiciary.gov.ph/feed/) — refreshes when upstream publishes.
CACHE_TTL_SC_JUDICIARY_FEED = int(os.getenv("CACHE_TTL_SC_JUDICIARY_FEED", "900"))  # 15 minutes
# Table-backed payload is stable; digest merge is rare. Long TTL = fewer DB reads & Redis rebuilds.
CACHE_TTL_FLASHCARD_CONCEPTS = int(os.getenv("CACHE_TTL_FLASHCARD_CONCEPTS", "86400"))  # default 24h
# LexCode / codal static JSON (legal text + link counts) — long TTL; bump key version on major ingest.
CACHE_TTL_CODAL_STATIC = int(os.getenv("CACHE_TTL_CODAL_STATIC", "86400"))  # default 24h

# PostgreSQL ThreadedConnectionPool — keep maxconn below Azure max_connections (reserve headroom per instance).
DB_POOL_MIN_CONN = int(os.getenv("DB_POOL_MIN_CONN", "2"))
DB_POOL_MAX_CONN = int(os.getenv("DB_POOL_MAX_CONN", "15"))

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

# ── RAG / Legal Expert AI ─────────────────────────────────────────────────────
GCP_PROJECT          = os.getenv("GCP_PROJECT", "gen-lang-client-0176283199")
GCP_LOCATION         = os.getenv("GCP_LOCATION", "us-central1")       # Gemini model calls
RAG_REGION           = os.getenv("RAG_REGION", "europe-west4")         # RAG Engine corpus (avoids Spanner capacity limit)
GCP_CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "lexmateph-rag-key.json")

# In Azure production, we cannot upload the JSON file via git.
# We read the raw JSON string from an App Setting and write it to a temporary file.
# GCP_SA_JSON_B64: base64-encoded service account JSON (preferred — survives shell escaping).
# GCP_SA_JSON:     raw JSON string (fallback for local dev / direct paste).
_gcp_sa_b64  = os.getenv("GCP_SA_JSON_B64", "").strip()
_gcp_sa_json = os.getenv("GCP_SA_JSON",     "").strip()

_sa_content = None
if _gcp_sa_b64:
    import base64
    try:
        _sa_content = base64.b64decode(_gcp_sa_b64).decode("utf-8")
    except Exception as _e:
        import logging
        logging.error(f"Failed to decode GCP_SA_JSON_B64: {_e}")
elif _gcp_sa_json:
    _sa_content = _gcp_sa_json

if _sa_content:
    import tempfile
    _tmp_key_path = os.path.join(tempfile.gettempdir(), "lexmateph-rag-key.json")
    try:
        with open(_tmp_key_path, "w", encoding="utf-8") as _f:
            _f.write(_sa_content)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp_key_path
        GCP_CREDENTIALS_FILE = _tmp_key_path
    except Exception as _e:
        import logging
        logging.error(f"Failed to write GCP SA JSON to temp file: {_e}")

# GCS
GCS_CORPUS_BUCKET    = os.getenv("GCS_CORPUS_BUCKET", "lexmateph-legal-corpus")
GCS_CASES_PREFIX     = "cases/full-text"
GCS_DIGESTS_PREFIX   = "cases/digests"
GCS_STATUTES_PREFIX  = "statutes/full-text"
GCS_PROVISIONS_PREFIX= "statutes/provisions"
GCS_BAR_PREFIX       = "bar-exam"

# Gemini models (Vertex AI — billed to GenAI App Builder credit)
GEMINI_PRO_MODEL     = os.getenv("GEMINI_PRO_MODEL",   "gemini-2.5-pro")
GEMINI_FLASH_MODEL   = os.getenv("GEMINI_FLASH_MODEL", "gemini-3-flash-preview")

# RAG Engine
RAG_CORPUS_NAME      = os.getenv("RAG_CORPUS_NAME", "")   # set after corpus creation
RAG_TOP_K            = int(os.getenv("RAG_TOP_K", "20"))
RAG_RERANK_TOP_K     = int(os.getenv("RAG_RERANK_TOP_K", "10"))
RAG_CHUNK_SIZE       = int(os.getenv("RAG_CHUNK_SIZE", "512"))
RAG_CHUNK_OVERLAP    = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))

# Complexity thresholds (1-5 scale)
COMPLEXITY_FLASH_MAX = int(os.getenv("COMPLEXITY_FLASH_MAX", "3"))  # ≤3 uses Flash, >3 uses Pro

# Semantic cache similarity threshold (0.0-1.0)
CACHE_SEMANTIC_THRESHOLD = float(os.getenv("CACHE_SEMANTIC_THRESHOLD", "0.92"))
CACHE_TTL_LEGAL_CHAT     = int(os.getenv("CACHE_TTL_LEGAL_CHAT", "604800"))  # 7 days

# Rate limits per plan (questions per day, -1 = unlimited)
RATE_LIMIT_GUEST  = int(os.getenv("RATE_LIMIT_GUEST",  "3"))
RATE_LIMIT_FREE   = int(os.getenv("RATE_LIMIT_FREE",  "10"))
RATE_LIMIT_AMICUS = int(os.getenv("RATE_LIMIT_AMICUS", "-1"))

# Budget guard thresholds (% of credit used)
BUDGET_WARN_PCT      = int(os.getenv("BUDGET_WARN_PCT",  "60"))
BUDGET_CAUTION_PCT   = int(os.getenv("BUDGET_CAUTION_PCT", "80"))
BUDGET_EMERGENCY_PCT = int(os.getenv("BUDGET_EMERGENCY_PCT", "95"))
CREDIT_TOTAL_EUR     = float(os.getenv("CREDIT_TOTAL_EUR", "855.05"))

# Logging
import logging
logging.info(f"Environment: {'LOCAL' if IS_LOCAL_DEV else 'PRODUCTION'}")
logging.info("Database: Cloud PostgreSQL (DB_CONNECTION_STRING)")
logging.info(f"Redis: {'Enabled' if REDIS_ENABLED else 'Disabled'}")
logging.info(f"RAG: project={GCP_PROJECT} location={GCP_LOCATION} bucket={GCS_CORPUS_BUCKET}")
