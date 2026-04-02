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
CACHE_TTL_FLASHCARD_CONCEPTS = int(os.getenv("CACHE_TTL_FLASHCARD_CONCEPTS", "3600"))  # 1 hour — heavy aggregation

# Logging
import logging
logging.info(f"Environment: {'LOCAL' if IS_LOCAL_DEV else 'PRODUCTION'}")
logging.info(f"Database: {'Local PostgreSQL' if IS_LOCAL_DEV else 'Azure PostgreSQL'}")
logging.info(f"Redis: {'Enabled' if REDIS_ENABLED else 'Disabled'}")
