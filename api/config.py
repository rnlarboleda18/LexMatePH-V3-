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

# ── Gemini (direct API — ai_search, digest, mock exam) ───────────────────────
GCP_PROJECT          = os.getenv("GCP_PROJECT", "project-d6b2ec19-4edd-4c2c-a00")
GCP_LOCATION         = os.getenv("GCP_LOCATION", "us")
GCP_CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "lexmateph-rag-key.json")
GEMINI_FLASH_MODEL   = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")

# Load service account JSON from env (Azure production — can't commit key file to git)
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

# ── Payments / Xendit ─────────────────────────────────────────────────────────
# Note: XENDIT_API_KEY is also read at request time inside xendit._xendit_headers()
# to pick up hot app-setting updates without a cold start; the module-level
# constant below is for config auditing and the pre-flight guard in create_checkout.
XENDIT_API_KEY       = os.getenv("XENDIT_API_KEY", "")
XENDIT_WEBHOOK_TOKEN = os.getenv("XENDIT_WEBHOOK_TOKEN", "")
XENDIT_BYPASS        = os.getenv("XENDIT_BYPASS", "").lower() in ("true", "1", "yes")

# ── Frontend / CORS ───────────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://lexmateph.com").rstrip("/")

# ── Admin bootstrap ───────────────────────────────────────────────────────────
# Fallback email list used only when auto-creating a user row before the Clerk
# webhook has fired. DB is_admin column is the authoritative source after sync.
_DEFAULT_ADMINS = {
    "rnlarboleda@gmail.com",
    "rnlarboleda18@gmail.com",
    "rnlarboleda28@gmail.com",
    "rnlarboleda10@gmail.com",
    "rnlarboleda6@gmail.com",
    "rnlarboleda11@gmail.com",
}
_configured_admins = os.getenv("ADMIN_EMAILS", "")
ADMIN_EMAILS_ENV = list(_DEFAULT_ADMINS | {
    e.strip().lower()
    for e in _configured_admins.split(",")
    if e.strip()
})

# ── Guest access ──────────────────────────────────────────────────────────────
GUEST_FULL_ACCESS_HOURS = int(os.getenv("GUEST_FULL_ACCESS_HOURS", "24"))

# ── Clerk ─────────────────────────────────────────────────────────────────────
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

# ── Azure Speech / LexPlay TTS ────────────────────────────────────────────────
SPEECH_KEY                       = os.getenv("SPEECH_KEY", "")
SPEECH_REGION                    = os.getenv("SPEECH_REGION", "japaneast")
LEXPLAY_USE_AZURE_SPEECH         = os.getenv("LEXPLAY_USE_AZURE_SPEECH", "").lower() in ("1", "true", "yes")
AZURE_STORAGE_CONNECTION_STRING  = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")

# Logging
import logging
logging.info(f"Environment: {'LOCAL' if IS_LOCAL_DEV else 'PRODUCTION'}")
logging.info("Database: Cloud PostgreSQL (DB_CONNECTION_STRING)")
logging.info(f"Redis: {'Enabled' if REDIS_ENABLED else 'Disabled'}")
logging.info(f"GCP: project={GCP_PROJECT} location={GCP_LOCATION}")
